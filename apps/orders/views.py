from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid

from apps.orders.models import Order, OrderItem, OrderStatusHistory, Payment
from apps.cart.utils import get_or_create_cart
from apps.cart.models import CartItem
from apps.accounts.models import Address
from apps.smart_features.budget_service import BudgetService
from apps.orders.invoice_generator import generate_order_invoice_pdf


@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)
    if not cart or cart.total_items == 0:
        messages.warning(request, "Your cart is empty. Add some products before checkout.")
        return redirect('catalogue:product_list')

    # Validate stock before allowing checkout
    for item in cart.items.all():
        if item.product.is_expired:
            messages.error(request, f"'{item.product.name}' is expired and cannot be ordered. Please remove it from cart.")
            return redirect('cart:cart_detail')
        if item.quantity > item.product.stock_quantity:
            messages.error(request, f"Insufficient stock for '{item.product.name}'. Available: {item.product.stock_quantity}.")
            return redirect('cart:cart_detail')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first() or addresses.first()
    budget_data = BudgetService.get_budget_dashboard_data(request.user, cart=cart)

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        delivery_slot = request.POST.get('delivery_slot', 'EXPRESS_15MIN')
        payment_method = request.POST.get('payment_method', 'COD')
        if delivery_slot not in dict(Order.DELIVERY_SLOT_CHOICES):
            delivery_slot = 'EXPRESS_15MIN'
        if payment_method not in dict(Order.PAYMENT_METHOD_CHOICES):
            payment_method = 'COD'
        order_notes = request.POST.get('order_notes', '').strip()

        # Resolve shipping address
        if address_id:
            shipping_address = get_object_or_404(Address, pk=address_id, user=request.user)
        elif default_address:
            shipping_address = default_address
        else:
            messages.error(request, "Please add a delivery address to complete your order.")
            return redirect('accounts:address_add')

        # Atomic transaction: Create order, snapshot data, reduce stock, record payment
        with transaction.atomic():
            # 1. Create Order
            order = Order.objects.create(
                user=request.user,
                status='PLACED',
                # Address snapshot
                shipping_full_name=shipping_address.full_name,
                shipping_phone=shipping_address.phone_number,
                shipping_street=shipping_address.street_address,
                shipping_landmark=shipping_address.landmark,
                shipping_city=shipping_address.city,
                shipping_state=shipping_address.state,
                shipping_postal_code=shipping_address.postal_code,
                # Preferences
                delivery_slot=delivery_slot,
                order_notes=order_notes,
                # Financial snapshots
                subtotal=cart.subtotal,
                product_discount=cart.product_savings,
                coupon_code=cart.coupon.code if cart.coupon else '',
                coupon_discount=cart.coupon_discount,
                delivery_fee=cart.delivery_fee,
                grand_total=cart.grand_total,
                payment_method=payment_method,
                payment_status='PAID' if payment_method in ['UPI', 'CARD'] else 'PENDING',
                transaction_id=f"TXN-{uuid.uuid4().hex[:10].upper()}" if payment_method in ['UPI', 'CARD'] else '',
            )

            # 2. Create OrderItems and reduce inventory
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_unit=item.product.unit,
                    unit_price=item.unit_price,
                    original_price=item.product.original_price,
                    quantity=item.quantity,
                    total_price=item.total_price,
                )
                # Inventory reduction
                prod = item.product
                prod.stock_quantity = max(0, prod.stock_quantity - item.quantity)
                prod.save(update_fields=['stock_quantity'])

                # If item was an expiry rescue deal, increment rescued count
                if hasattr(prod, 'expiry_deal') and prod.expiry_deal.is_currently_active:
                    deal = prod.expiry_deal
                    deal.rescued_count += item.quantity
                    deal.save(update_fields=['rescued_count'])

            # 3. Create initial status history
            OrderStatusHistory.objects.create(
                order=order,
                status='PLACED',
                comment="Order placed by customer via web portal.",
                updated_by=request.user
            )

            # 4. Record Payment simulation
            Payment.objects.create(
                order=order,
                transaction_id=order.transaction_id or f"COD-{order.order_number}",
                payment_method=payment_method,
                amount=order.grand_total,
                status='PAID' if payment_method in ['UPI', 'CARD'] else 'PENDING',
                simulation_notes="Simulated payment processed for college major project evaluation."
            )

            # 5. Increment coupon usage if used
            if cart.coupon:
                cart.coupon.used_count += 1
                cart.coupon.save(update_fields=['used_count'])

            # 6. Clear cart
            cart.items.all().delete()
            cart.coupon = None
            cart.save()

        # Notifications: order placed + monthly budget alert (if this order crossed a limit)
        from apps.core.notifications import notify_order_status, notify_budget_if_needed
        notify_order_status(order, 'PLACED')
        notify_budget_if_needed(request.user, BudgetService.get_budget_dashboard_data(request.user))

        messages.success(request, f"Order #{order.order_number} placed successfully!")
        return redirect('orders:confirmation', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'addresses': addresses,
        'default_address': default_address,
        'budget_data': budget_data,
        'delivery_slots': Order.DELIVERY_SLOT_CHOICES,
        'payment_methods': Order.PAYMENT_METHOD_CHOICES,
    })


@login_required
def order_confirmation_view(request, order_number):
    order = get_object_or_404(Order.objects.select_related('user'), order_number=order_number, user=request.user)
    return render(request, 'orders/order_confirmation.html', {'order': order})


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(Order.objects.select_related('delivery_partner'), order_number=order_number, user=request.user)
    status_history = order.status_history.all().order_by('created_at')
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'status_history': status_history,
    })


@login_required
def order_tracking_view(request, order_number):
    order = get_object_or_404(Order.objects.select_related('delivery_partner'), order_number=order_number, user=request.user)
    
    # Tracking steps definition
    tracking_steps = [
        {'status': 'PLACED', 'label': 'Order Placed', 'icon': 'bi-receipt'},
        {'status': 'CONFIRMED', 'label': 'Order Confirmed', 'icon': 'bi-check-circle'},
        {'status': 'PACKING', 'label': 'Packing at Hub', 'icon': 'bi-box-seam'},
        {'status': 'ASSIGNED', 'label': 'Delivery Partner Assigned', 'icon': 'bi-person-badge'},
        {'status': 'PICKED_UP', 'label': 'Picked Up', 'icon': 'bi-bag-check'},
        {'status': 'OUT_FOR_DELIVERY', 'label': 'Out for Delivery', 'icon': 'bi-bicycle'},
        {'status': 'DELIVERED', 'label': 'Delivered', 'icon': 'bi-house-check'},
    ]

    status_order = ['PLACED', 'CONFIRMED', 'PACKING', 'READY_FOR_PICKUP', 'ASSIGNED', 'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED']
    # Map every order status onto the visible timeline step (fixes the old off-by-N mismatch where
    # e.g. 'Picked Up' highlighted the 'Delivered' step because the two lists had different lengths).
    step_index = {
        'PLACED': 0, 'CONFIRMED': 1, 'PACKING': 2, 'READY_FOR_PICKUP': 2, 'ASSIGNED': 3,
        'PICKED_UP': 4, 'OUT_FOR_DELIVERY': 5, 'DELIVERED': len(tracking_steps),  # all steps completed
    }
    current_idx = step_index.get(order.status, 0) if order.status in status_order else 0

    return render(request, 'orders/order_tracking.html', {
        'order': order,
        'tracking_steps': tracking_steps,
        'current_status': order.status,
        'current_idx': current_idx,
        'eta_minutes': estimate_eta_minutes(order),
    })


@login_required
@require_POST
def cancel_order_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if not order.is_cancellable:
        messages.error(request, f"Order #{order.order_number} cannot be cancelled as it is already {order.get_status_display().lower()}.")
        return redirect('orders:order_detail', order_number=order_number)

    reason = request.POST.get('cancellation_reason', 'Cancelled by customer').strip() or 'Cancelled by customer'

    # Order.cancel() restores inventory, refunds prepaid payments (simulated),
    # writes status history and sends a notification - all inside one transaction.
    order.cancel(reason=reason, user=request.user)

    messages.info(request, f"Order #{order.order_number} has been cancelled and items returned to stock.")
    return redirect('orders:order_detail', order_number=order_number)


@login_required
def download_invoice_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    # Check permissions
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "Unauthorized access to order invoice.")
        return redirect('core:home')

    return generate_order_invoice_pdf(order)


# ==========================================
# ADDED: Live tracking JSON (polled every few seconds by the tracking page)
# and one-click "Order Again"
# ==========================================

# Simulated minutes-to-door for an express order at each stage
EXPRESS_ETA_BY_STATUS = {
    'PLACED': 18, 'CONFIRMED': 16, 'PACKING': 13, 'READY_FOR_PICKUP': 11,
    'ASSIGNED': 10, 'PICKED_UP': 8, 'OUT_FOR_DELIVERY': 5, 'DELIVERED': 0, 'CANCELLED': 0,
}


def estimate_eta_minutes(order):
    """Simple, explainable ETA model used for the live tracking card."""
    if order.delivery_slot != 'EXPRESS_15MIN':
        return None  # scheduled slot -> show the slot instead of a countdown
    base = EXPRESS_ETA_BY_STATUS.get(order.status, 15)
    if base == 0:
        return 0
    # minutes already spent in the current stage reduce the ETA a little (never below 1)
    last = order.status_history.order_by('-created_at').first()
    minutes_in_stage = 0
    if last:
        minutes_in_stage = int((timezone.now() - last.created_at).total_seconds() // 60)
    return max(1, base - min(minutes_in_stage, 3))


@login_required
def order_status_api(request, order_number):
    order = get_object_or_404(Order.objects.select_related('delivery_partner'), order_number=order_number)
    if order.user != request.user and order.delivery_partner != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Not allowed'}, status=403)
    partner = order.delivery_partner
    return JsonResponse({
        'success': True,
        'order_number': order.order_number,
        'status': order.status,
        'status_label': order.get_status_display(),
        'progress_percent': order.progress_percent,
        'eta_minutes': estimate_eta_minutes(order),
        'delivery_slot': order.get_delivery_slot_display(),
        'partner': (partner.get_full_name() or partner.username) if partner else None,
        'history': [
            {'status': h.status, 'label': h.get_status_display(), 'time': timezone.localtime(h.created_at).strftime('%I:%M %p'),
             'comment': h.comment}
            for h in order.status_history.all()
        ],
    })


@login_required
@require_POST
def reorder_view(request, order_number):
    """Blinkit-style 'Order Again': copy every still-available item of a past order into the cart."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart = get_or_create_cart(request)
    added, skipped = 0, []
    for item in order.items.select_related('product'):
        prod = item.product
        if not prod or not prod.is_active or not prod.is_in_stock:
            skipped.append(item.product_name)
            continue
        qty = min(item.quantity, prod.stock_quantity)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=prod, defaults={'quantity': qty})
        if not created:
            cart_item.quantity = min(max(cart_item.quantity, qty), prod.stock_quantity)
            cart_item.save()
        added += 1
    if added:
        messages.success(request, f"Added {added} item(s) from order #{order.order_number} to your cart.")
    if skipped:
        messages.warning(request, "Unavailable right now: " + ", ".join(skipped[:4]) + ("…" if len(skipped) > 4 else "")
                         + ". Check Smart Substitution for alternatives.")
    return redirect('cart:cart_detail')

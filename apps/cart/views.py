from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from decimal import Decimal

from apps.catalogue.models import Product
from apps.cart.models import Cart, CartItem, Coupon, Wishlist, WishlistItem
from apps.cart.utils import get_or_create_cart
from apps.smart_features.budget_service import BudgetService


def cart_detail_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product', 'product__category') if cart else []

    # Check budget status for logged in customer
    budget_data = None
    if request.user.is_authenticated:
        budget_data = BudgetService.get_budget_dashboard_data(request.user, cart=cart)

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'cart_items': cart_items,
        'budget_data': budget_data,
    })


@require_POST
def add_to_cart_view(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))

    product = get_object_or_404(Product, pk=product_id, is_active=True)

    # 1. Validation: Expired product check
    if product.is_expired:
        messages.error(request, f"Sorry, '{product.name}' is past its expiry date and cannot be purchased.")
        return redirect(request.META.get('HTTP_REFERER', 'catalogue:product_list'))

    # 2. Validation: Out of stock check
    if product.stock_quantity <= 0:
        messages.error(request, f"Sorry, '{product.name}' is currently out of stock.")
        return redirect('smart_features:substitution_detail', product_id=product.id)

    # Cap quantity to available stock
    if quantity > product.stock_quantity:
        quantity = product.stock_quantity
        messages.warning(request, f"Only {product.stock_quantity} units available in stock.")

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            new_quantity = product.stock_quantity
            messages.warning(request, f"Reached maximum available stock ({product.stock_quantity} units) for '{product.name}'.")
        cart_item.quantity = new_quantity
        cart_item.save()

    messages.success(request, f"Added {quantity}x '{product.name}' to your cart!")

    # If AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.total_items,
            'message': f"Added '{product.name}' to cart!"
        })

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cart:cart_detail'
    return redirect(next_url)


@require_POST
def update_cart_item_view(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    action = request.POST.get('action') # 'increase', 'decrease', 'set'

    if action == 'increase':
        if cart_item.quantity < cart_item.product.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"Updated quantity for '{cart_item.product.name}'.")
        else:
            messages.warning(request, f"Cannot add more. Only {cart_item.product.stock_quantity} units in stock.")
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            messages.success(request, f"Updated quantity for '{cart_item.product.name}'.")
        else:
            cart_item.delete()
            messages.info(request, f"Removed '{cart_item.product.name}' from your cart.")
    elif action == 'set':
        try:
            qty = int(request.POST.get('quantity', 1))
            if qty <= 0:
                cart_item.delete()
                messages.info(request, f"Removed '{cart_item.product.name}' from your cart.")
            else:
                cart_item.quantity = min(qty, cart_item.product.stock_quantity)
                cart_item.save()
                messages.success(request, f"Updated quantity for '{cart_item.product.name}'.")
        except Exception:
            pass

    return redirect('cart:cart_detail')


@require_POST
def remove_cart_item_view(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f"Removed '{product_name}' from your cart.")
    return redirect('cart:cart_detail')


@require_POST
def apply_coupon_view(request):
    cart = get_or_create_cart(request)
    code = request.POST.get('coupon_code', '').strip().upper()

    if not code:
        messages.error(request, "Please enter a coupon code.")
        return redirect('cart:cart_detail')

    coupon = Coupon.objects.filter(code__iexact=code).first()
    if not coupon:
        messages.error(request, f"Coupon code '{code}' is invalid or does not exist.")
        return redirect('cart:cart_detail')

    valid, msg = coupon.is_valid(subtotal=cart.subtotal)
    if valid:
        cart.coupon = coupon
        cart.save()
        messages.success(request, f"Coupon '{coupon.code}' applied! You saved ₹{cart.coupon_discount}.")
    else:
        messages.error(request, msg)

    return redirect('cart:cart_detail')


@require_POST
def remove_coupon_view(request):
    cart = get_or_create_cart(request)
    if cart and cart.coupon:
        cart.coupon = None
        cart.save()
        messages.info(request, "Coupon removed from your cart.")
    return redirect('cart:cart_detail')


@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    items = wishlist.items.all().select_related('product', 'product__category')
    return render(request, 'cart/wishlist.html', {
        'wishlist': wishlist,
        'items': items,
    })


@login_required
@require_POST
def toggle_wishlist_view(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, pk=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    item = WishlistItem.objects.filter(wishlist=wishlist, product=product).first()
    if item:
        item.delete()
        messages.info(request, f"Removed '{product.name}' from your wishlist.")
        added = False
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f"Added '{product.name}' to your wishlist!")
        added = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'added': added,
            'wishlist_count': wishlist.total_items,
            'message': f"{'Added to' if added else 'Removed from'} wishlist"
        })

    return redirect(request.META.get('HTTP_REFERER', 'catalogue:product_list'))


# ==========================================
# ADDED: Blinkit-style instant cart API
# Product cards turn "ADD" into a  [ - 2 + ]  stepper without reloading the page.
# Both endpoints return the same JSON "cart summary" so the navbar badge and the
# floating "View Cart" bar can update instantly.
# ==========================================

def _cart_summary(cart):
    return {
        'cart_count': cart.total_items if cart else 0,
        'subtotal': str(cart.subtotal if cart else Decimal('0.00')),
        'grand_total': str(cart.grand_total if cart else Decimal('0.00')),
        'delivery_fee': str(cart.delivery_fee if cart else Decimal('0.00')),
        'free_delivery_gap': str(max(Decimal('0.00'), Decimal('499.00') - (cart.subtotal if cart else Decimal('0.00')))),
    }


def cart_state_api(request):
    """GET -> quantities of every product currently in the cart: {"items": {"12": 2, ...}, ...summary}"""
    cart = get_or_create_cart(request)
    items = {}
    if cart:
        for item in cart.items.all():
            items[str(item.product_id)] = item.quantity
    data = {'success': True, 'items': items}
    data.update(_cart_summary(cart))
    return JsonResponse(data)


@require_POST
def cart_set_quantity_api(request):
    """
    POST product_id, quantity -> sets the exact quantity of a product in the cart.
    quantity = 0 removes the item. Quantity is capped at available stock.
    """
    try:
        product_id = int(request.POST.get('product_id', 0))
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid product or quantity.'}, status=400)

    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if not product:
        return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)

    cart = get_or_create_cart(request)
    item = CartItem.objects.filter(cart=cart, product=product).first()
    message = ''

    if quantity <= 0:
        if item:
            item.delete()
        quantity = 0
        message = f"Removed '{product.name}'"
    else:
        if product.is_expired:
            return JsonResponse({'success': False, 'message': f"'{product.name}' is past its expiry date."}, status=400)
        if product.stock_quantity <= 0:
            return JsonResponse({'success': False, 'message': f"'{product.name}' is out of stock.",
                                 'substitute_url': f"/smart/substitute/{product.id}/"}, status=400)
        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            message = f"Only {product.stock_quantity} units of '{product.name}' available."
        if item:
            item.quantity = quantity
            item.save(update_fields=['quantity', 'updated_at'])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=quantity)
        message = message or f"'{product.name}' x{quantity} in cart"

    data = {'success': True, 'product_id': product.id, 'quantity': quantity,
            'max_quantity': product.stock_quantity, 'message': message}
    data.update(_cart_summary(cart))
    return JsonResponse(data)

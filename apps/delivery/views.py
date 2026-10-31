from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.accounts.decorators import delivery_required
from apps.orders.models import Order, DeliveryAssignment, OrderStatusHistory
from apps.accounts.models import DeliveryProfile


@delivery_required
def delivery_dashboard_view(request):
    user = request.user
    profile, _ = DeliveryProfile.objects.get_or_create(user=user)

    today = timezone.now().date()
    assigned_orders = Order.objects.filter(delivery_partner=user).exclude(status__in=['DELIVERED', 'CANCELLED'])
    completed_today = Order.objects.filter(delivery_partner=user, status='DELIVERED', delivered_at__date=today).count()
    total_completed = Order.objects.filter(delivery_partner=user, status='DELIVERED').count()

    pending_pickups = assigned_orders.filter(status__in=['ASSIGNED', 'READY_FOR_PICKUP']).count()
    out_for_delivery = assigned_orders.filter(status='OUT_FOR_DELIVERY').count()

    return render(request, 'delivery/dashboard.html', {
        'profile': profile,
        'assigned_orders': assigned_orders,
        'completed_today': completed_today,
        'total_completed': total_completed,
        'pending_pickups': pending_pickups,
        'out_for_delivery': out_for_delivery,
    })


@delivery_required
def delivery_order_detail_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, delivery_partner=request.user)
    return render(request, 'delivery/order_detail.html', {'order': order})


@delivery_required
@require_POST
def update_delivery_status_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, delivery_partner=request.user)
    new_status = request.POST.get('status')
    comment = request.POST.get('comment', '').strip()

    valid_transitions = {
        'ASSIGNED': ['PICKED_UP'],
        'READY_FOR_PICKUP': ['PICKED_UP'],
        'PICKED_UP': ['OUT_FOR_DELIVERY'],
        'OUT_FOR_DELIVERY': ['DELIVERED'],
    }

    if order.status in valid_transitions and new_status in valid_transitions[order.status]:
        order.add_status_history(
            new_status=new_status,
            comment=comment or f"Status updated to {dict(Order.STATUS_CHOICES).get(new_status, new_status)} by delivery partner.",
            user=request.user
        )
        messages.success(request, f"Order #{order.order_number} status updated to '{order.get_status_display()}'.")
    else:
        messages.error(request, f"Cannot transition order from {order.get_status_display()} to {new_status}.")

    return redirect('delivery:order_detail', order_number=order.order_number)


@delivery_required
def completed_deliveries_view(request):
    completed_orders = Order.objects.filter(delivery_partner=request.user, status='DELIVERED').order_by('-delivered_at')
    return render(request, 'delivery/completed_orders.html', {'orders': completed_orders})


@delivery_required
def delivery_profile_view(request):
    profile, _ = DeliveryProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profile.phone = request.POST.get('phone', profile.phone)
        profile.vehicle_type = request.POST.get('vehicle_type', profile.vehicle_type)
        profile.vehicle_number = request.POST.get('vehicle_number', profile.vehicle_number)
        profile.is_available = 'is_available' in request.POST
        profile.save()
        messages.success(request, "Delivery profile updated successfully.")
        return redirect('delivery:profile')

    return render(request, 'delivery/profile.html', {'profile': profile})

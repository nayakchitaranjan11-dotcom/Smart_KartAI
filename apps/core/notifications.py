"""
Notification Engine
-------------------
Single place that creates in-app notifications (the bell icon in the navbar).

Events that trigger a notification:
    * Order placed / every order status change  -> customer        (type ORDER)
    * Order assigned to a rider                 -> delivery partner (type ORDER)
    * Monthly budget crosses warning % / 100 %  -> customer        (type BUDGET)
    * Wishlisted product gets an Expiry Rescue  -> customer        (type RESCUE)
    * Welcome message on registration           -> customer        (type SYSTEM)
"""

from django.utils import timezone

from apps.core.models import Notification

# Friendly customer-facing text for every order status
ORDER_STATUS_MESSAGES = {
    'PLACED': ("Order placed successfully", "We have received your order and will confirm it shortly."),
    'CONFIRMED': ("Order confirmed", "Your order is confirmed and will be packed at our dark store."),
    'PACKING': ("Packing your items", "Our store team is packing your groceries right now."),
    'READY_FOR_PICKUP': ("Packed & ready", "Your order is packed and waiting for a delivery partner."),
    'ASSIGNED': ("Delivery partner assigned", "A delivery partner has been assigned to your order."),
    'PICKED_UP': ("Order picked up", "Your delivery partner has picked up the order from the store."),
    'OUT_FOR_DELIVERY': ("Out for delivery", "Your order is on the way! Keep your phone handy."),
    'DELIVERED': ("Order delivered", "Your order has been delivered. Enjoy your groceries!"),
    'CANCELLED': ("Order cancelled", "Your order was cancelled. Any prepaid amount is refunded (simulated)."),
}


def notify(user, title, message, notification_type='SYSTEM', link_url=''):
    """Create one notification. Silently ignores missing users so callers stay simple."""
    if user is None:
        return None
    return Notification.objects.create(
        user=user,
        title=title[:150],
        message=message,
        notification_type=notification_type,
        link_url=link_url or '',
    )


def notify_order_status(order, status=None):
    """Tell the customer (and the rider when assigned) about an order status change."""
    status = status or order.status
    title, message = ORDER_STATUS_MESSAGES.get(status, ("Order updated", f"Status changed to {status}."))
    tracking_url = f"/orders/{order.order_number}/tracking/"
    notify(
        order.user,
        f"#{order.order_number}: {title}",
        message,
        notification_type='ORDER',
        link_url=tracking_url,
    )
    if status == 'ASSIGNED' and order.delivery_partner_id:
        notify(
            order.delivery_partner,
            f"New delivery: #{order.order_number}",
            f"Pick up {order.total_items_count} item(s) for {order.shipping_full_name}, "
            f"{order.shipping_city} - {order.shipping_postal_code}.",
            notification_type='ORDER',
            link_url=f"/delivery/order/{order.order_number}/",
        )


def notify_budget_if_needed(user, budget_data):
    """
    Sends at most one 'warning' and one 'exceeded' budget alert per user per month.
    `budget_data` is the dict returned by BudgetService.get_budget_dashboard_data().
    """
    if not budget_data:
        return None
    now = timezone.now()
    this_month = Notification.objects.filter(
        user=user, notification_type='BUDGET',
        created_at__year=now.year, created_at__month=now.month,
    )
    link = '/smart/budget/'
    if budget_data.get('is_exceeded'):
        if not this_month.filter(title__icontains='exceeded').exists():
            return notify(
                user, "Monthly budget exceeded",
                f"You have spent ₹{budget_data['spent_this_month']} of your ₹{budget_data['budget_amount']} "
                f"budget for {budget_data['month_name']}. Try the Money Saver swaps to cut costs.",
                'BUDGET', link,
            )
    elif budget_data.get('actual_percent_used', 0) >= budget_data.get('warning_threshold_percent', 80):
        if not this_month.filter(title__icontains='threshold').exists():
            return notify(
                user, f"Budget threshold reached ({budget_data['actual_percent_used']}%)",
                f"Only ₹{budget_data['remaining_budget']} left in your {budget_data['month_name']} grocery budget.",
                'BUDGET', link,
            )
    return None


def notify_wishlist_rescue_deal(deal):
    """Alert every customer who wishlisted a product that it is now on an Expiry Rescue deal."""
    from apps.cart.models import WishlistItem
    product = deal.product
    users = (WishlistItem.objects.filter(product=product)
             .select_related('wishlist__user').values_list('wishlist__user', flat=True).distinct())
    from django.contrib.auth.models import User
    count = 0
    for user in User.objects.filter(pk__in=list(users)):
        notify(
            user, f"Rescue deal on your wishlist: {product.name}",
            f"Now ₹{deal.rescue_price} ({deal.rescue_discount_percent}% OFF) until {deal.end_date:%d %b}. Grab it before it's gone!",
            'RESCUE', '/smart/expiry-deals/',
        )
        count += 1
    return count

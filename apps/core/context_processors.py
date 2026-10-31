from apps.catalogue.models import Category
from apps.cart.models import Cart, Wishlist
from apps.core.models import Notification
from apps.smart_features.models import MonthlyBudget
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal


def global_context(request):
    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    cart_count = 0
    cart = None
    wishlist_count = 0
    unread_notifications = 0
    user_role = 'GUEST'
    user_budget_summary = None

    # Safe cart retrieval
    try:
        from apps.cart.utils import get_or_create_cart
        cart = get_or_create_cart(request)
        cart_count = cart.total_items if cart else 0
    except Exception:
        cart = None
        cart_count = 0

    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            user_role = 'ADMIN'
        elif hasattr(request.user, 'delivery_profile'):
            user_role = 'DELIVERY'
        else:
            user_role = 'CUSTOMER'

        # Wishlist count
        try:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist_count = wishlist.total_items
        except Exception:
            wishlist_count = 0

        # Notifications
        try:
            unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
        except Exception:
            unread_notifications = 0

        # Budget quick info for customer
        try:
            now = timezone.now()
            budget = MonthlyBudget.objects.filter(user=request.user, month=now.month, year=now.year).first()
            if not budget and hasattr(request.user, 'customer_profile'):
                profile_budget = request.user.customer_profile.monthly_budget
                budget, _ = MonthlyBudget.objects.get_or_create(
                    user=request.user,
                    month=now.month,
                    year=now.year,
                    defaults={'budget_amount': profile_budget}
                )

            if budget:
                from apps.orders.models import Order
                spent_result = Order.objects.filter(
                    user=request.user,
                    created_at__year=now.year,
                    created_at__month=now.month
                ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))

                spent_amount = spent_result['total'] or Decimal('0.00')
                remaining = max(Decimal('0.00'), budget.budget_amount - spent_amount)
                percent_used = int(round((spent_amount / budget.budget_amount * 100))) if budget.budget_amount > 0 else 0

                user_budget_summary = {
                    'budget_amount': budget.budget_amount,
                    'spent_amount': spent_amount,
                    'remaining_amount': remaining,
                    'percent_used': percent_used,
                    'is_warning': percent_used >= budget.warning_threshold_percent,
                    'is_exceeded': spent_amount > budget.budget_amount,
                }
        except Exception:
            user_budget_summary = None

    return {
        'nav_categories': categories[:10],
        'all_categories': categories,
        'cart': cart,
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'unread_notifications_count': unread_notifications,
        'user_role': user_role,
        'user_budget_summary': user_budget_summary,
        'currency_symbol': '₹',
    }

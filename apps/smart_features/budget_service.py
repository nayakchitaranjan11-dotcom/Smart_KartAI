"""
Monthly Budget Smart Cart Service
---------------------------------
Analyzes customer shopping budget, tracks delivered and active order spending,
projects cart impact, generates category-level spending analytics,
and detects high-cost cart items with money-saving cheaper alternatives.
"""

from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from apps.orders.models import Order
from apps.smart_features.models import MonthlyBudget
from apps.catalogue.models import Product


class BudgetService:
    @staticmethod
    def get_budget_dashboard_data(user, cart=None):
        """
        Returns full analytics and budget metrics for the customer.
        """
        now = timezone.now()
        current_month = now.month
        current_year = now.year

        # Get or create current monthly budget
        budget_obj = MonthlyBudget.objects.filter(user=user, month=current_month, year=current_year).first()
        if not budget_obj:
            default_amount = Decimal('5000.00')
            if hasattr(user, 'customer_profile'):
                default_amount = user.customer_profile.monthly_budget
            budget_obj = MonthlyBudget.objects.create(
                user=user,
                month=current_month,
                year=current_year,
                budget_amount=default_amount,
                warning_threshold_percent=80
            )

        budget_amount = budget_obj.budget_amount
        warning_threshold_percent = budget_obj.warning_threshold_percent

        # 1. Spent this month (Delivered + Active orders excluding Cancelled)
        current_month_orders = Order.objects.filter(
            user=user,
            created_at__year=current_year,
            created_at__month=current_month
        ).exclude(status='CANCELLED')

        spent_this_month = current_month_orders.aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

        # 2. Previous month spending for comparison
        prev_month = 12 if current_month == 1 else current_month - 1
        prev_year = current_year - 1 if current_month == 1 else current_year

        prev_month_orders = Order.objects.filter(
            user=user,
            created_at__year=prev_year,
            created_at__month=prev_month
        ).exclude(status='CANCELLED')

        spent_prev_month = prev_month_orders.aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')

        # 3. Cart projected impact
        cart_total = cart.grand_total if cart else Decimal('0.00')
        projected_total = spent_this_month + cart_total
        remaining_budget = max(Decimal('0.00'), budget_amount - spent_this_month)
        projected_remaining = budget_amount - projected_total

        percent_used = int(round((spent_this_month / budget_amount * 100))) if budget_amount > 0 else 0
        projected_percent_used = int(round((projected_total / budget_amount * 100))) if budget_amount > 0 else 0

        # Status flags
        is_exceeded = spent_this_month > budget_amount
        is_approaching = percent_used >= warning_threshold_percent and not is_exceeded
        will_exceed_with_cart = projected_total > budget_amount and not is_exceeded

        # 4. Category-wise spending breakdown
        category_spending = {}
        for order in current_month_orders:
            for item in order.items.all():
                if item.product and item.product.category:
                    cat_name = item.product.category.name
                else:
                    cat_name = "Groceries & General"
                category_spending[cat_name] = category_spending.get(cat_name, Decimal('0.00')) + item.total_price

        # Format category data for Chart.js
        category_labels = list(category_spending.keys())
        category_values = [float(val) for val in category_spending.values()]

        # Find top spending category
        top_category = None
        if category_spending:
            top_category = max(category_spending.items(), key=lambda x: x[1])

        # 5. "Save Money" smart recommendations for items in current cart
        money_saver_suggestions = []
        if cart:
            for cart_item in cart.items.all():
                prod = cart_item.product
                # Find in-stock cheaper alternative in same category with comparable pack
                cheaper_alternatives = Product.objects.filter(
                    category=prod.category,
                    is_active=True,
                    stock_quantity__gt=0,
                    selling_price__lt=prod.selling_price
                ).exclude(pk=prod.pk).order_by('selling_price')[:2]

                for alt in cheaper_alternatives:
                    savings_per_unit = prod.selling_price - alt.selling_price
                    total_potential_savings = savings_per_unit * cart_item.quantity
                    money_saver_suggestions.append({
                        'cart_item': cart_item,
                        'original_product': prod,
                        'cheaper_product': alt,
                        'savings_per_unit': savings_per_unit,
                        'total_savings': total_potential_savings,
                        'pack_info': f"{alt.unit} vs {prod.unit}",
                    })

        return {
            'budget': budget_obj,
            'budget_amount': budget_amount,
            'spent_this_month': spent_this_month,
            'spent_prev_month': spent_prev_month,
            'cart_total': cart_total,
            'projected_total': projected_total,
            'remaining_budget': remaining_budget,
            'projected_remaining': projected_remaining,
            'percent_used': min(percent_used, 100),
            'actual_percent_used': percent_used,
            'projected_percent_used': min(projected_percent_used, 100),
            'is_approaching': is_approaching,
            'is_exceeded': is_exceeded,
            'will_exceed_with_cart': will_exceed_with_cart,
            'warning_threshold_percent': warning_threshold_percent,
            'category_labels': category_labels,
            'category_values': category_values,
            'top_category': top_category,
            'money_saver_suggestions': money_saver_suggestions[:4],
            'month_name': now.strftime('%B %Y'),
        }

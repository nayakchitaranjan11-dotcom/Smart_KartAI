"""
Expiry Rescue Deals Service
---------------------------
Manages perishable food rescue deals to minimize grocery waste,
calculates dynamic urgency countdowns with color codes (Red: <=1 day, Orange: <=3 days, Yellow: <=7 days),
automatically locks expired inventory from purchase, and generates near-expiry alerts for administrators.
"""

from decimal import Decimal
from django.utils import timezone
from apps.smart_features.models import ExpiryRescueDeal
from apps.catalogue.models import Product
import datetime


class ExpiryRescueService:
    @staticmethod
    def get_active_deals():
        """
        Returns all active, non-expired rescue deals with in-stock products.
        """
        today = timezone.now().date()
        deals = ExpiryRescueDeal.objects.filter(
            is_active=True,
            expiry_date__gte=today,
            product__stock_quantity__gt=0,
            product__is_active=True
        ).select_related('product', 'product__category', 'product__brand').order_by('expiry_date')

        # Auto-deactivate any truly expired deals in database
        ExpiryRescueDeal.objects.filter(expiry_date__lt=today, is_active=True).update(is_active=False)

        return deals

    @staticmethod
    def get_total_rescued_items_count():
        """
        Calculates total number of food items rescued from waste across all deals.
        """
        deals = ExpiryRescueDeal.objects.all()
        return sum(d.rescued_count for d in deals)

    @staticmethod
    def get_admin_expiry_alerts():
        """
        Returns categorized near-expiry and expired alerts for admin dashboard.
        - Expired (Requires immediate removal)
        - Critical (Expiring within 1-3 days)
        - Warning (Expiring within 4-7 days)
        """
        today = timezone.now().date()
        seven_days_later = today + datetime.timedelta(days=7)
        three_days_later = today + datetime.timedelta(days=3)

        # Products with expiry dates
        products_with_expiry = Product.objects.filter(
            is_active=True,
            expiry_date__isnull=False
        ).select_related('category', 'brand')

        expired = []
        critical = []
        warning = []

        for prod in products_with_expiry:
            if prod.expiry_date < today:
                expired.append(prod)
            elif today <= prod.expiry_date <= three_days_later:
                critical.append(prod)
            elif three_days_later < prod.expiry_date <= seven_days_later:
                warning.append(prod)

        return {
            'expired': expired,
            'critical': critical,
            'warning': warning,
            'total_alerts_count': len(expired) + len(critical) + len(warning),
        }

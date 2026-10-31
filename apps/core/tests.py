from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Notification, ContactMessage
from apps.core.notifications import notify, notify_budget_if_needed, notify_wishlist_rescue_deal
from apps.core.templatetags.core_tags import emoji_for_product, recipe_emoji
from apps.core.testing_helpers import make_customer, make_product
from apps.cart.models import Wishlist, WishlistItem
from apps.smart_features.models import ExpiryRescueDeal, Recipe


class PublicPagesTests(TestCase):
    def test_home_about_contact_render(self):
        make_product()
        for name in ('core:home', 'core:about', 'core:contact'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_contact_form_saves_message(self):
        self.client.post(reverse('core:contact'), {'name': 'A', 'email': 'a@b.com', 'subject': 'Hi', 'message': 'Help'})
        self.assertEqual(ContactMessage.objects.count(), 1)


class NotificationTests(TestCase):
    def setUp(self):
        self.user = make_customer('neha')

    def test_notifications_page_shows_then_marks_read(self):
        notify(self.user, 'Hello', 'World')
        self.client.login(username='neha', password='testpass123')
        resp = self.client.get(reverse('core:notifications'))
        self.assertContains(resp, 'Hello')
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())

    def test_budget_alert_sent_only_once_per_month(self):
        data = {'is_exceeded': True, 'spent_this_month': Decimal('6000'), 'budget_amount': Decimal('5000'),
                'month_name': 'October 2026', 'actual_percent_used': 120, 'warning_threshold_percent': 80,
                'remaining_budget': Decimal('0')}
        notify_budget_if_needed(self.user, data)
        notify_budget_if_needed(self.user, data)
        self.assertEqual(Notification.objects.filter(user=self.user, notification_type='BUDGET').count(), 1)

    def test_wishlist_customers_hear_about_rescue_deal(self):
        product = make_product(name='Fresh Paneer', price='80', mrp='90', expiry_days=2)
        WishlistItem.objects.create(wishlist=Wishlist.objects.create(user=self.user), product=product)
        deal = ExpiryRescueDeal.objects.create(product=product, rescue_discount_percent=50, rescue_price=Decimal('0'),
                                               expiry_date=product.expiry_date, end_date=product.expiry_date)
        self.assertEqual(notify_wishlist_rescue_deal(deal), 1)
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type='RESCUE').exists())


class ProductVisualTests(TestCase):
    def test_emoji_by_name_then_category(self):
        self.assertEqual(emoji_for_product(make_product(name='Fresh Hybrid Tomatoes')), '🍅')
        self.assertEqual(emoji_for_product(make_product(name='Mystery Dairy Item')), '🥛')  # category fallback
        self.assertEqual(recipe_emoji(Recipe(name='Masala Chai')), '☕')

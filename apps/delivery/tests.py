from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import DeliveryProfile
from apps.core.models import Notification
from apps.core.testing_helpers import make_customer, make_product, make_rider, make_order


class DeliveryPortalTests(TestCase):
    def setUp(self):
        self.customer = make_customer('kiran')
        self.rider = make_rider('rider1')
        self.order = make_order(self.customer, [(make_product(), 2)], status='ASSIGNED', rider=self.rider)
        self.client.login(username='rider1', password='testpass123')

    def test_customer_cannot_open_delivery_portal(self):
        self.client.logout()
        self.client.login(username='kiran', password='testpass123')
        resp = self.client.get(reverse('delivery:dashboard'))
        self.assertRedirects(resp, reverse('core:home'))

    def test_dashboard_and_order_detail_render(self):
        self.assertContains(self.client.get(reverse('delivery:dashboard')), self.order.order_number)
        resp = self.client.get(reverse('delivery:order_detail', args=[self.order.order_number]))
        self.assertContains(resp, 'Open in Maps')
        self.assertContains(resp, 'cash')  # COD collection hint

    def test_full_delivery_flow_updates_profile_and_notifies_customer(self):
        url = reverse('delivery:update_status', args=[self.order.order_number])
        for status in ('PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED'):
            self.client.post(url, {'status': status})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'DELIVERED')
        self.assertEqual(self.order.payment_status, 'PAID')  # COD collected on delivery
        self.assertEqual(DeliveryProfile.objects.get(user=self.rider).total_deliveries, 1)
        self.assertEqual(Notification.objects.filter(user=self.customer, notification_type='ORDER').count(), 3)
        self.assertIn('Picked Up', self.order.status_history.filter(status='PICKED_UP').first().comment)

    def test_invalid_transition_is_blocked(self):
        self.client.post(reverse('delivery:update_status', args=[self.order.order_number]), {'status': 'DELIVERED'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ASSIGNED')

    def test_rider_cannot_see_other_riders_orders(self):
        other = make_rider('rider2')
        order2 = make_order(self.customer, [(make_product(name='Bread'), 1)], status='ASSIGNED', rider=other)
        resp = self.client.get(reverse('delivery:order_detail', args=[order2.order_number]))
        self.assertEqual(resp.status_code, 404)

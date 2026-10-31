from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Address, CustomerProfile
from apps.core.models import Notification
from apps.core.testing_helpers import make_customer


class RegistrationAndLoginTests(TestCase):
    def test_registration_creates_profile_budget_and_welcome_notification(self):
        resp = self.client.post(reverse('accounts:register'), {
            'username': 'asha', 'first_name': 'Asha', 'last_name': 'K', 'email': 'asha@example.com',
            'phone': '9999999999', 'password': 'Strong#Pass1', 'confirm_password': 'Strong#Pass1',
            'monthly_budget': '4500',
        })
        self.assertRedirects(resp, reverse('core:home'))
        user = User.objects.get(username='asha')
        self.assertEqual(str(user.customer_profile.monthly_budget), '4500.00')
        self.assertTrue(Notification.objects.filter(user=user, notification_type='SYSTEM').exists())

    def test_password_mismatch_is_rejected(self):
        self.client.post(reverse('accounts:register'), {
            'username': 'bad', 'first_name': 'B', 'last_name': 'C', 'email': 'b@example.com',
            'phone': '1', 'password': 'abc12345', 'confirm_password': 'different1',
        })
        self.assertFalse(User.objects.filter(username='bad').exists())

    def test_login_with_email_works(self):
        make_customer('ravi')
        resp = self.client.post(reverse('accounts:login'), {'username_or_email': 'ravi@example.com', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_ignores_external_next_url(self):
        """Security: ?next=https://evil.example must not redirect off-site (open redirect)."""
        make_customer('ravi')
        resp = self.client.post(reverse('accounts:login') + '?next=https://evil.example/steal',
                                {'username_or_email': 'ravi', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.example', resp['Location'])

    def test_login_follows_internal_next_url(self):
        make_customer('ravi')
        resp = self.client.post(reverse('accounts:login') + '?next=/cart/',
                                {'username_or_email': 'ravi', 'password': 'testpass123'})
        self.assertEqual(resp['Location'], '/cart/')


class AddressTests(TestCase):
    def test_only_one_default_address(self):
        user = make_customer('meena')
        second = Address.objects.create(user=user, full_name='Office', phone_number='1', street_address='x',
                                        postal_code='110002', is_default=True)
        self.assertEqual(Address.objects.filter(user=user, is_default=True).count(), 1)
        self.assertTrue(Address.objects.get(pk=second.pk).is_default)

    def test_profile_auto_created_by_signal(self):
        user = User.objects.create_user('signal', password='x12345678')
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

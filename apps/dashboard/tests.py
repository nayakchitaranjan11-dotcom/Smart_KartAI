from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.cart.models import Coupon
from apps.catalogue.models import Category, Product
from apps.core.models import ContactMessage
from apps.core.testing_helpers import make_admin, make_customer, make_product, make_rider, make_order
from apps.orders.models import Order
from apps.smart_features.models import Recipe


class AdminAccessTests(TestCase):
    def test_customer_is_blocked(self):
        make_customer('cust')
        self.client.login(username='cust', password='testpass123')
        self.assertRedirects(self.client.get(reverse('dashboard:admin_dashboard')), reverse('core:home'))

    def test_every_admin_page_renders(self):
        make_admin()
        product = make_product()
        order = make_order(make_customer('c1'), [(product, 1)])
        recipe = Recipe.objects.create(name='Poha', description='d', instructions='cook')
        self.client.login(username='boss', password='testpass123')
        names = ['admin_dashboard', 'products_list', 'product_create', 'categories_list', 'inventory', 'orders_list',
                 'customers_list', 'delivery_staff_list', 'coupons_list', 'recipes_list', 'recipe_create',
                 'expiry_deals_list', 'reviews_list', 'alerts', 'contact_messages', 'export_sales_csv']
        for name in names:
            self.assertEqual(self.client.get(reverse(f'dashboard:{name}')).status_code, 200, name)
        self.assertEqual(self.client.get(reverse('dashboard:recipe_edit', args=[recipe.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard:category_edit', args=[product.category.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard:order_detail', args=[order.order_number])).status_code, 200)
        self.assertEqual(self.client.get('/admin/catalogue/product/').status_code, 200)  # Django admin registered


class AdminActionsTests(TestCase):
    def setUp(self):
        make_admin()
        self.client.login(username='boss', password='testpass123')

    def test_recipe_create_edit_delete(self):
        milk = make_product()
        self.client.post(reverse('dashboard:recipe_create'), {
            'name': 'Masala Chai', 'diet_type': 'VEG', 'difficulty': 'EASY', 'base_servings': '2',
            'instructions': 'Boil', 'ing_name': ['Milk', 'Water'], 'ing_qty': ['250', '200'],
            'ing_unit': ['ml', 'ml'], 'ing_product': [str(milk.pk), ''], 'ing_notes': ['', ''], 'ing_optional': ['1']})
        recipe = Recipe.objects.get(name='Masala Chai')
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertTrue(recipe.ingredients.get(ingredient_name='Water').is_optional)
        self.client.post(reverse('dashboard:recipe_edit', args=[recipe.pk]), {
            'name': 'Kadak Chai', 'base_servings': '2', 'ing_name': ['Milk'], 'ing_qty': ['300'],
            'ing_unit': ['ml'], 'ing_product': [str(milk.pk)], 'ing_notes': ['']})
        recipe.refresh_from_db()
        self.assertEqual((recipe.name, recipe.ingredients.count()), ('Kadak Chai', 1))
        self.client.post(reverse('dashboard:recipe_delete', args=[recipe.pk]))
        self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_category_edit_and_coupon_toggle(self):
        cat = Category.objects.create(name='Bakery')
        self.client.post(reverse('dashboard:category_edit', args=[cat.pk]), {'name': 'Bakery & Cakes', 'icon_class': 'bi-cake'})
        cat.refresh_from_db()
        self.assertEqual((cat.name, cat.is_active), ('Bakery & Cakes', False))
        self.client.post(reverse('dashboard:coupons_list'), {'code': 'diwali', 'description': 'Festive', 'discount_type': 'PERCENT',
                                                             'discount_value': '10', 'min_order_value': '0', 'valid_to': '2030-12-31'})
        coupon = Coupon.objects.get(code='DIWALI')
        self.assertIsNotNone(coupon.valid_to.tzinfo)  # timezone-aware date
        self.client.post(reverse('dashboard:coupon_toggle', args=[coupon.pk]))
        coupon.refresh_from_db()
        self.assertFalse(coupon.is_active)

    def test_admin_cancel_restores_stock_and_refunds(self):
        product = make_product(stock=10)
        order = make_order(make_customer('c2'), [(product, 3)], payment_method='UPI')
        self.client.post(reverse('dashboard:order_detail', args=[order.order_number]),
                         {'action': 'update_status', 'status': 'CANCELLED', 'comment': 'Out of area'})
        order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual((order.status, order.payment_status, product.stock_quantity), ('CANCELLED', 'REFUNDED', 13))

    def test_invalid_status_is_rejected(self):
        order = make_order(make_customer('c3'), [(make_product(), 1)])
        self.client.post(reverse('dashboard:order_detail', args=[order.order_number]),
                         {'action': 'update_status', 'status': 'TELEPORTED'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'PLACED')

    def test_assign_rider_and_toggle_duty(self):
        rider = make_rider()
        order = make_order(make_customer('c4'), [(make_product(), 1)])
        self.client.post(reverse('dashboard:order_detail', args=[order.order_number]),
                         {'action': 'assign_delivery', 'delivery_partner_id': rider.pk})
        order.refresh_from_db()
        self.assertEqual((order.status, order.delivery_partner), ('ASSIGNED', rider))
        self.client.post(reverse('dashboard:delivery_partner_toggle', args=[rider.pk]))
        rider.delivery_profile.refresh_from_db()
        self.assertFalse(rider.delivery_profile.is_available)

    def test_contact_inbox_resolve(self):
        msg = ContactMessage.objects.create(name='A', email='a@b.com', subject='S', message='M')
        self.assertContains(self.client.get(reverse('dashboard:contact_messages')), 'M')
        self.client.post(reverse('dashboard:contact_message_toggle', args=[msg.pk]))
        msg.refresh_from_db()
        self.assertTrue(msg.is_resolved)


class RevenueChartTests(TestCase):
    def test_six_distinct_calendar_months(self):
        make_admin()
        self.client.login(username='boss', password='testpass123')
        labels = self.client.get(reverse('dashboard:admin_dashboard')).context['month_labels']
        self.assertEqual(len(labels), 6)
        self.assertEqual(len(set(labels)), 6)   # used to repeat the current month on the 31st

    def test_chart_script_rendered_once(self):
        make_admin()
        self.client.login(username='boss', password='testpass123')
        html = self.client.get(reverse('dashboard:admin_dashboard')).content.decode()
        self.assertEqual(html.count("getElementById('adminRevenueChart')"), 1)

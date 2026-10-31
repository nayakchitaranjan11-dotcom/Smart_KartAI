import decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from apps.catalogue.models import Category, Brand, Product
from apps.cart.models import Cart, CartItem, Coupon

class CartAndCouponTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='testpassword')
        self.category = Category.objects.create(name='Snacks', slug='snacks')
        self.brand = Brand.objects.create(name='Haldirams', slug='haldirams')
        self.product1 = Product.objects.create(
            name='Haldirams Bhujia 400g',
            slug='haldirams-bhujia-400g',
            category=self.category,
            brand=self.brand,
            description='Crispy authentic namkeen.',
            original_price=decimal.Decimal('100.00'),
            selling_price=decimal.Decimal('90.00'),
            stock_quantity=20,
            unit='400 g',
            is_active=True
        )
        self.product2 = Product.objects.create(
            name='Haldirams Gulab Jamun 1kg',
            slug='haldirams-gulab-jamun-1kg',
            category=self.category,
            brand=self.brand,
            description='Sweet soft gulab jamuns in sugar syrup.',
            original_price=decimal.Decimal('250.00'),
            selling_price=decimal.Decimal('220.00'),
            stock_quantity=10,
            unit='1 kg',
            is_active=True
        )
        self.cart = Cart.objects.create(user=self.user)
        self.item1 = CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        self.item2 = CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)

    def test_cart_item_total_price(self):
        # 2 * 90.00 = 180.00
        self.assertEqual(self.item1.total_price, decimal.Decimal('180.00'))
        # 1 * 220.00 = 220.00
        self.assertEqual(self.item2.total_price, decimal.Decimal('220.00'))

    def test_cart_totals_and_delivery_charge(self):
        # Subtotal = 180 + 220 = 400.00
        self.assertEqual(self.cart.subtotal, decimal.Decimal('400.00'))
        # Subtotal < 499 => delivery fee 30.00
        self.assertEqual(self.cart.delivery_fee, decimal.Decimal('30.00'))
        # Grand total = 400 + 30 = 430.00
        self.assertEqual(self.cart.grand_total, decimal.Decimal('430.00'))

    def test_percentage_coupon(self):
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='PERCENT',
            discount_value=decimal.Decimal('10.00'),
            min_order_value=decimal.Decimal('200.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=5),
            is_active=True
        )
        discount = coupon.calculate_discount(self.cart.subtotal) # 10% of 400 = 40.00
        self.assertEqual(discount, decimal.Decimal('40.00'))

    def test_flat_coupon(self):
        coupon = Coupon.objects.create(
            code='FLAT50',
            discount_type='FLAT',
            discount_value=decimal.Decimal('50.00'),
            min_order_value=decimal.Decimal('300.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=5),
            is_active=True
        )
        discount = coupon.calculate_discount(self.cart.subtotal)
        self.assertEqual(discount, decimal.Decimal('50.00'))


# ---------------------------------------------------------------------------
# Added: instant cart API (ADD -> [- 1 +] stepper)
# ---------------------------------------------------------------------------
from django.urls import reverse  # noqa: E402
from apps.core.testing_helpers import make_product as _make_product  # noqa: E402


class InstantCartApiTests(TestCase):
    def setUp(self):
        self.product = _make_product(stock=3)

    def test_set_quantity_caps_at_stock_and_zero_removes(self):
        url = reverse('cart:api_set_quantity')
        data = self.client.post(url, {'product_id': self.product.pk, 'quantity': 2}).json()
        self.assertEqual((data['quantity'], data['cart_count']), (2, 2))
        data = self.client.post(url, {'product_id': self.product.pk, 'quantity': 10}).json()
        self.assertEqual(data['quantity'], 3)           # capped at stock
        state = self.client.get(reverse('cart:api_state')).json()
        self.assertEqual(state['items'][str(self.product.pk)], 3)
        data = self.client.post(url, {'product_id': self.product.pk, 'quantity': 0}).json()
        self.assertEqual(data['cart_count'], 0)

    def test_out_of_stock_returns_substitute_link(self):
        self.product.stock_quantity = 0
        self.product.save()
        resp = self.client.post(reverse('cart:api_set_quantity'), {'product_id': self.product.pk, 'quantity': 1})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('/smart/substitute/', resp.json()['substitute_url'])

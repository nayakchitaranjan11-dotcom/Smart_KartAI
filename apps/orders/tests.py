import decimal
from django.test import TestCase
from django.contrib.auth.models import User
from apps.catalogue.models import Category, Brand, Product
from apps.accounts.models import Address
from apps.orders.models import Order, OrderItem

class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ordertester', password='testpassword')
        self.category = Category.objects.create(name='Fruits & Vegetables', slug='fruits-vegetables')
        self.brand = Brand.objects.create(name='Farm Fresh', slug='farm-fresh')
        self.product = Product.objects.create(
            name='Fresh Organic Onion 1kg',
            slug='fresh-organic-onion-1kg',
            category=self.category,
            brand=self.brand,
            description='Farm fresh organic red onions.',
            original_price=decimal.Decimal('40.00'),
            selling_price=decimal.Decimal('35.00'),
            stock_quantity=50,
            unit='1 kg',
            is_active=True
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test Buyer',
            phone_number='9876543210',
            street_address='Flat 101, Green Heights',
            city='Bangalore',
            state='Karnataka',
            postal_code='560001'
        )

    def test_order_creation_and_stock(self):
        order = Order.objects.create(
            user=self.user,
            shipping_full_name=self.address.full_name,
            shipping_phone=self.address.phone_number,
            shipping_street=self.address.street_address,
            shipping_city=self.address.city,
            shipping_state=self.address.state,
            shipping_postal_code=self.address.postal_code,
            subtotal=decimal.Decimal('70.00'),
            delivery_fee=decimal.Decimal('30.00'),
            grand_total=decimal.Decimal('100.00'),
            status='PLACED'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            product_unit=self.product.unit,
            unit_price=self.product.selling_price,
            original_price=self.product.original_price,
            quantity=2,
            total_price=decimal.Decimal('70.00')
        )
        # Deduct stock
        self.product.stock_quantity -= 2
        self.product.save()

        self.assertEqual(order.items.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 48)

    def test_order_cancellation_restores_stock(self):
        order = Order.objects.create(
            user=self.user,
            shipping_full_name=self.address.full_name,
            shipping_phone=self.address.phone_number,
            shipping_street=self.address.street_address,
            shipping_city=self.address.city,
            shipping_state=self.address.state,
            shipping_postal_code=self.address.postal_code,
            subtotal=decimal.Decimal('175.00'),
            delivery_fee=decimal.Decimal('30.00'),
            grand_total=decimal.Decimal('205.00'),
            status='PLACED'
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            product_unit=self.product.unit,
            unit_price=self.product.selling_price,
            original_price=self.product.original_price,
            quantity=5,
            total_price=decimal.Decimal('175.00')
        )
        self.product.stock_quantity -= 5
        self.product.save()

        # Cancel order
        order.status = 'CANCELLED'
        order.save()
        # Restore stock
        for order_item in order.items.all():
            if order_item.product:
                order_item.product.stock_quantity += order_item.quantity
                order_item.product.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 50)


# ---------------------------------------------------------------------------
# Added: cancellation refunds, live tracking API, reorder, notifications
# ---------------------------------------------------------------------------
from django.urls import reverse  # noqa: E402
from apps.core.models import Notification  # noqa: E402
from apps.cart.models import Cart  # noqa: E402
from apps.core.testing_helpers import make_customer, make_product as _mp, make_order  # noqa: E402


class OrderLifecycleTests(TestCase):
    def setUp(self):
        self.user = make_customer('anita')
        self.product = _mp(stock=20)
        self.client.login(username='anita', password='testpass123')

    def test_checkout_creates_order_reduces_stock_and_notifies(self):
        self.client.post(reverse('cart:add_to_cart'), {'product_id': self.product.pk, 'quantity': 4})
        resp = self.client.post(reverse('orders:checkout'), {'payment_method': 'UPI', 'delivery_slot': 'NOT_A_SLOT'})
        order = Order.objects.get(user=self.user)
        self.assertRedirects(resp, reverse('orders:confirmation', args=[order.order_number]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 16)
        self.assertEqual(order.delivery_slot, 'EXPRESS_15MIN')   # invalid slot falls back safely
        self.assertTrue(Notification.objects.filter(user=self.user, title__icontains='placed').exists())

    def test_customer_cancel_refunds_prepaid_and_restores_stock(self):
        order = make_order(self.user, [(self.product, 5)], payment_method='CARD')
        self.client.post(reverse('orders:cancel_order', args=[order.order_number]), {'cancellation_reason': 'Changed mind'})
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual((order.status, order.payment_status), ('CANCELLED', 'REFUNDED'))
        self.assertEqual(self.product.stock_quantity, 25)
        self.assertFalse(order.cancel())  # cancelling twice does nothing

    def test_tracking_page_and_status_api(self):
        order = make_order(self.user, [(self.product, 1)], status='PICKED_UP')
        resp = self.client.get(reverse('orders:order_tracking', args=[order.order_number]))
        # 'Picked Up' must be the ACTIVE step (index 4), not 'Delivered'
        self.assertEqual(resp.context['current_idx'], 4)
        self.assertEqual(resp.context['tracking_steps'][4]['status'], 'PICKED_UP')
        data = self.client.get(reverse('orders:order_status_api', args=[order.order_number])).json()
        self.assertEqual(data['status'], 'PICKED_UP')
        self.assertGreater(data['progress_percent'], 50)
        self.assertGreaterEqual(data['eta_minutes'], 1)

    def test_other_users_cannot_read_status_api(self):
        order = make_order(make_customer('someone'), [(self.product, 1)])
        resp = self.client.get(reverse('orders:order_status_api', args=[order.order_number]))
        self.assertEqual(resp.status_code, 403)

    def test_order_again_copies_available_items(self):
        gone = _mp(name='Discontinued Bread', stock=0)
        order = make_order(self.user, [(self.product, 2), (gone, 1)], status='DELIVERED')
        self.client.post(reverse('orders:reorder', args=[order.order_number]))
        cart = Cart.objects.get(user=self.user)
        self.assertEqual([(i.product, i.quantity) for i in cart.items.all()], [(self.product, 2)])

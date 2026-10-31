"""
Small factory helpers shared by the automated tests (kept out of test*.py so the
test runner does not treat this file as a test module).
"""

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.models import Address, DeliveryProfile
from apps.catalogue.models import Category, Brand, Product
from apps.orders.models import Order, OrderItem, OrderStatusHistory, Payment


def make_category(name='Dairy & Breakfast'):
    return Category.objects.get_or_create(name=name)[0]


def make_product(name='Amul Taaza Toned Milk', price='30.00', mrp='32.00', stock=50, unit='500 ml',
                 category=None, brand=None, expiry_days=None, **extra):
    category = category or make_category()
    expiry = timezone.localdate() + datetime.timedelta(days=expiry_days) if expiry_days is not None else None
    return Product.objects.create(
        name=name, category=category, brand=brand, description=f'{name} description',
        original_price=Decimal(mrp), selling_price=Decimal(price), unit=unit,
        stock_quantity=stock, expiry_date=expiry, **extra,
    )


def make_brand(name='Amul'):
    return Brand.objects.get_or_create(name=name)[0]


def make_customer(username='priya', password='testpass123', **extra):
    user = User.objects.create_user(username=username, password=password,
                                    email=f'{username}@example.com', first_name=username.title(), **extra)
    Address.objects.create(user=user, full_name=user.first_name, phone_number='9876543210',
                           street_address='Flat 1, Test Street', city='New Delhi', state='Delhi',
                           postal_code='110001', is_default=True)
    return user


def make_admin(username='boss', password='testpass123'):
    return User.objects.create_user(username=username, password=password, is_staff=True, is_superuser=True)


def make_rider(username='rider', password='testpass123'):
    user = User.objects.create_user(username=username, password=password, first_name='Rahul')
    DeliveryProfile.objects.create(user=user, phone='9000000000', vehicle_number='DL1')
    return user


def make_order(user, items, status='PLACED', payment_method='COD', rider=None, created_at=None):
    """items = [(product, qty), ...]  -> creates an order snapshot (stock is NOT changed)."""
    subtotal = sum(p.selling_price * q for p, q in items)
    order = Order.objects.create(
        user=user, status=status, shipping_full_name=user.first_name or user.username,
        shipping_phone='9876543210', shipping_street='Flat 1, Test Street', shipping_city='New Delhi',
        shipping_state='Delhi', shipping_postal_code='110001', subtotal=subtotal,
        delivery_fee=Decimal('0.00'), grand_total=subtotal, payment_method=payment_method,
        payment_status='PAID' if payment_method in ('UPI', 'CARD') else 'PENDING',
        delivery_partner=rider,
    )
    for product, qty in items:
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
                                 product_unit=product.unit, unit_price=product.selling_price,
                                 original_price=product.original_price, quantity=qty,
                                 total_price=product.selling_price * qty)
    OrderStatusHistory.objects.create(order=order, status=status, comment='test')
    Payment.objects.create(order=order, transaction_id=f'TEST-{order.order_number}', payment_method=payment_method,
                           amount=order.grand_total, status=order.payment_status)
    if created_at:
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        order.refresh_from_db()
    return order

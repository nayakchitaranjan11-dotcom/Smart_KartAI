import decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.catalogue.models import Category, Brand, Product

class CatalogueModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Dairy & Breakfast', slug='dairy-breakfast', display_order=1)
        self.brand = Brand.objects.create(name='Amul', slug='amul')
        self.product = Product.objects.create(
            name='Amul Taaza Fresh Toned Milk 500ml',
            slug='amul-taaza-fresh-toned-milk-500ml',
            category=self.category,
            brand=self.brand,
            description='Fresh toned milk pasteurized and packed.',
            original_price=decimal.Decimal('28.00'),
            selling_price=decimal.Decimal('27.00'),
            stock_quantity=50,
            unit='500 ml',
            is_active=True,
            expiry_date=timezone.now().date() + timedelta(days=3)
        )

    def test_product_discount_percentage(self):
        self.assertEqual(self.product.discount_percent, 4)

    def test_product_in_stock(self):
        self.assertTrue(self.product.is_in_stock)
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)

    def test_product_expired(self):
        self.assertFalse(self.product.is_expired)
        self.product.expiry_date = timezone.now().date() - timedelta(days=1)
        self.product.save()
        self.assertTrue(self.product.is_expired)

    def test_category_slug_and_str(self):
        self.assertEqual(str(self.category), 'Dairy & Breakfast')
        self.assertEqual(self.category.slug, 'dairy-breakfast')


# ---------------------------------------------------------------------------
# Added regression tests (pages that used to crash)
# ---------------------------------------------------------------------------
from django.urls import reverse  # noqa: E402
from apps.core.testing_helpers import make_product as _make_product  # noqa: E402


class CatalogueListingRegressionTests(TestCase):
    def setUp(self):
        _make_product(name='Cheap Milk', price='20', mrp='40')     # 50% off
        _make_product(name='Fancy Milk', price='95', mrp='100')    # 5% off

    def test_all_products_page_renders(self):
        """Used to crash with 'Invalid filter: make_list_split' (missing {% load core_tags %})."""
        self.assertEqual(self.client.get(reverse('catalogue:product_list')).status_code, 200)

    def test_sort_by_discount_orders_biggest_discount_first(self):
        """Used to crash with FieldError: 'discount_percentage' is not a database field."""
        resp = self.client.get(reverse('catalogue:product_list') + '?sort=discount')
        self.assertEqual(resp.status_code, 200)
        names = [p.name for p in resp.context['page_obj']]
        self.assertLess(names.index('Cheap Milk'), names.index('Fancy Milk'))

    def test_suggestion_api_returns_emoji(self):
        data = self.client.get(reverse('catalogue:search_suggestions') + '?term=milk').json()
        self.assertTrue(data['results'][0]['emoji'])

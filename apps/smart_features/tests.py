import decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.catalogue.models import Category, Brand, Product
from apps.cart.models import Cart, CartItem
from apps.smart_features.models import MonthlyBudget, Recipe, RecipeIngredient, ExpiryRescueDeal
from apps.smart_features.ocr_scanner import OCRGroceryScanner
from apps.smart_features.budget_service import BudgetService
from apps.smart_features.recipe_service import RecipeService
from apps.smart_features.substitution_engine import SubstitutionEngine
from apps.smart_features.expiry_service import ExpiryRescueService

class SmartFeaturesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='smartuser', password='password123')
        self.cat_dairy = Category.objects.create(name='Dairy & Breakfast', slug='dairy-breakfast')
        self.cat_staples = Category.objects.create(name='Atta, Rice & Dal', slug='atta-rice-dal')
        self.brand_amul = Brand.objects.create(name='Amul', slug='amul')
        self.brand_mother = Brand.objects.create(name='Mother Dairy', slug='mother-dairy')
        self.brand_aashirvaad = Brand.objects.create(name='Aashirvaad', slug='aashirvaad')

        self.milk1 = Product.objects.create(
            name='Amul Taaza Fresh Toned Milk 500ml',
            slug='amul-taaza-fresh-toned-milk-500ml',
            category=self.cat_dairy,
            brand=self.brand_amul,
            description='Fresh toned milk pasteurized.',
            original_price=decimal.Decimal('28.00'),
            selling_price=decimal.Decimal('27.00'),
            stock_quantity=50,
            unit='500 ml',
            unit_value=decimal.Decimal('500.00'),
            unit_type='ml',
            nutritional_tags='milk,toned,dairy,amul',
            average_rating=decimal.Decimal('4.80'),
            is_active=True
        )

        self.milk2 = Product.objects.create(
            name='Mother Dairy Toned Milk 500ml',
            slug='mother-dairy-toned-milk-500ml',
            category=self.cat_dairy,
            brand=self.brand_mother,
            description='Homogenized toned milk.',
            original_price=decimal.Decimal('28.00'),
            selling_price=decimal.Decimal('27.00'),
            stock_quantity=40,
            unit='500 ml',
            unit_value=decimal.Decimal('500.00'),
            unit_type='ml',
            nutritional_tags='milk,toned,dairy,fresh',
            average_rating=decimal.Decimal('4.70'),
            is_active=True
        )

        self.atta = Product.objects.create(
            name='Aashirvaad Superior Sharbati Atta 5kg',
            slug='aashirvaad-superior-sharbati-atta-5kg',
            category=self.cat_staples,
            brand=self.brand_aashirvaad,
            description='Whole wheat chakki atta.',
            original_price=decimal.Decimal('295.00'),
            selling_price=decimal.Decimal('265.00'),
            stock_quantity=30,
            unit='5 kg',
            unit_value=decimal.Decimal('5.00'),
            unit_type='kg',
            nutritional_tags='atta,flour,wheat,staples',
            average_rating=decimal.Decimal('4.90'),
            is_active=True
        )

    def test_ocr_text_parser_and_fuzzy_matcher(self):
        sample_text = """
        1. Amul Milk - 2 pkts
        2. Aashirvaad Atta - 1 bag
        """
        parsed_items = OCRGroceryScanner.parse_full_list(sample_text)
        self.assertEqual(len(parsed_items), 2)
        
        # Check first item matching
        first_item = parsed_items[0]
        self.assertEqual(first_item['quantity'], decimal.Decimal('2.00'))
        self.assertIsNotNone(first_item['product'])
        self.assertEqual(first_item['product'].id, self.milk1.id)
        self.assertGreaterEqual(first_item['confidence'], 50.0)

    def test_smart_substitution_engine(self):
        # Simulate milk1 being out of stock
        self.milk1.stock_quantity = 0
        self.milk1.save()

        substitutes = SubstitutionEngine.get_substitutes(self.milk1, limit=3)
        self.assertGreaterEqual(len(substitutes), 1)
        top_sub = substitutes[0]
        self.assertEqual(top_sub['product'].id, self.milk2.id)
        self.assertGreaterEqual(top_sub['score'], 50.0)
        self.assertTrue(len(top_sub['all_reasons']) > 0)

    def test_budget_service_calculations(self):
        now = timezone.now()
        budget = MonthlyBudget.objects.create(
            user=self.user,
            month=now.month,
            year=now.year,
            budget_amount=decimal.Decimal('5000.00'),
            warning_threshold_percent=80
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.atta, quantity=2) # 265 * 2 = 530.00

        data = BudgetService.get_budget_dashboard_data(self.user, cart)
        self.assertEqual(data['budget_amount'], decimal.Decimal('5000.00'))
        self.assertEqual(data['cart_total'], decimal.Decimal('530.00'))
        self.assertEqual(data['projected_remaining'], decimal.Decimal('4470.00'))
        self.assertFalse(data['is_exceeded'])

    def test_recipe_scaling_service(self):
        recipe = Recipe.objects.create(
            name='Classic Chai',
            slug='classic-chai',
            base_servings=2,
            difficulty='EASY',
            prep_time_minutes=5,
            cook_time_minutes=10,
            instructions='Boil milk and water with tea leaves and spices.'
        )
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient_name='Toned Milk',
            quantity_per_base_servings=decimal.Decimal('250.00'),
            unit='ml',
            product=self.milk1
        )

        scaled_data = RecipeService.get_recipe_ingredients_data(recipe, target_servings=4)
        self.assertEqual(scaled_data['target_servings'], 4)
        self.assertEqual(len(scaled_data['ingredients']), 1)
        # Scaled qty = 250 * 2 = 500.00
        self.assertEqual(scaled_data['ingredients'][0]['scaled_quantity'], decimal.Decimal('500.00'))

    def test_expiry_rescue_deal_urgency(self):
        rescue_deal = ExpiryRescueDeal.objects.create(
            product=self.milk1,
            rescue_discount_percent=40,
            rescue_price=decimal.Decimal('16.20'),
            expiry_date=timezone.now().date() + timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=1),
            is_active=True
        )
        self.assertEqual(rescue_deal.rescue_price, decimal.Decimal('16.20'))
        self.assertEqual(rescue_deal.urgency_level, 'danger')


# ---------------------------------------------------------------------------
# Added: unit conversion, servings-aware Recipe-to-Cart, recommendations,
#        budget settings regression
# ---------------------------------------------------------------------------
from decimal import Decimal  # noqa: E402
from django.urls import reverse  # noqa: E402
from apps.cart.models import Cart  # noqa: E402
from apps.core.testing_helpers import make_customer, make_product as _mp, make_order  # noqa: E402
from apps.smart_features.units import packs_needed, parse_pack_size  # noqa: E402
from apps.smart_features.recommendation_engine import RecommendationEngine  # noqa: E402
from apps.smart_features.recipe_service import RecipeService  # noqa: E402


class UnitConversionTests(TestCase):
    def test_pack_parsing(self):
        self.assertEqual(parse_pack_size('1 kg'), (1000.0, 'weight'))
        self.assertEqual(parse_pack_size('500 ml'), (500.0, 'volume'))
        self.assertEqual(parse_pack_size('2 x 200 ml'), (400.0, 'volume'))
        self.assertEqual(parse_pack_size('1 Pack'), (None, None))

    def test_packs_needed(self):
        tomatoes = _mp(name='Tomatoes', unit='1 kg')
        self.assertEqual(packs_needed(400, 'g', tomatoes), 1)
        self.assertEqual(packs_needed(1200, 'g', tomatoes), 2)
        self.assertEqual(packs_needed(2, 'kg', tomatoes), 2)
        self.assertEqual(packs_needed(4, 'piece', tomatoes), 1)   # incompatible units -> 1 pack


class ServingsAwareRecipeTests(TestCase):
    def test_more_servings_add_more_packs(self):
        paneer = _mp(name='Fresh Paneer', unit='200 g', stock=10)
        recipe = Recipe.objects.create(name='Paneer Tikka', description='d', instructions='grill', base_servings=4)
        ing = RecipeIngredient.objects.create(recipe=recipe, product=paneer, ingredient_name='Paneer',
                                              quantity_per_base_servings=Decimal('200'), unit='g')
        info4 = RecipeService.get_recipe_ingredients_data(recipe, 4)
        info8 = RecipeService.get_recipe_ingredients_data(recipe, 8)
        self.assertEqual(info4['ingredients'][0]['packs_needed'], 1)
        self.assertEqual(info8['ingredients'][0]['packs_needed'], 2)
        self.assertEqual(recipe.calculate_cost_for_servings(8), paneer.selling_price * 2)
        self.client.post(reverse('smart_features:recipe_add_to_cart', args=[recipe.slug]),
                         {'servings': 8, 'ingredient_id': [str(ing.pk)]})
        self.assertEqual(Cart.objects.get().items.get().quantity, 2)


class RecommendationTests(TestCase):
    def test_frequently_bought_together_uses_order_history(self):
        user = make_customer('fbt')
        bread, butter, jam = _mp(name='Bread'), _mp(name='Butter'), _mp(name='Jam')
        make_order(user, [(bread, 1), (butter, 1)])
        make_order(user, [(bread, 1), (butter, 1), (jam, 1)])
        recs = RecommendationEngine.frequently_bought_together(bread)
        self.assertEqual(recs[0]['product'], butter)
        self.assertEqual(recs[0]['confidence'], 100)
        again = RecommendationEngine.buy_again(user)
        self.assertEqual(set(again[:2]), {bread, butter})   # bought twice each
        self.assertEqual(again[2], jam)                       # bought once


class BudgetSettingsRegressionTests(TestCase):
    def test_update_budget_settings_saves(self):
        """Used to fail with NameError: name 'timezone' is not defined."""
        make_customer('budgeter')
        self.client.login(username='budgeter', password='testpass123')
        self.client.post(reverse('smart_features:update_budget'), {'budget_amount': '7500', 'warning_threshold_percent': '70'})
        budget = MonthlyBudget.objects.get(user__username='budgeter')
        self.assertEqual((budget.budget_amount, budget.warning_threshold_percent), (Decimal('7500'), 70))

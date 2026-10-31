"""
Management command to seed the database with rich Indian quick-commerce grocery datasets,
recipes, coupons, user roles, sample orders, and expiry rescue deals for SmartKart AI.
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

from apps.accounts.models import CustomerProfile, DeliveryProfile, Address
from apps.catalogue.models import Category, Brand, Product, Review
from apps.cart.models import Coupon
from apps.orders.models import Order, OrderItem, OrderStatusHistory, Payment, DeliveryAssignment
from apps.smart_features.models import Recipe, RecipeIngredient, MonthlyBudget, ExpiryRescueDeal


class Command(BaseCommand):
    help = 'Seeds database with realistic grocery catalogue, recipes, coupons, users, and orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh-dates', action='store_true',
            help="Re-base demo expiry dates on TODAY for products that already exist. "
                 "Use this when you demo the project weeks after seeding and fresh items show as expired.",
        )

    def handle(self, *args, **options):
        refresh_dates = options.get('refresh_dates', False)
        self.stdout.write(self.style.NOTICE("Beginning SmartKart AI database seeding..."))

        # 1. Create User Roles
        self.stdout.write("Creating user accounts...")
        
        # Superuser / Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@smartkart.ai',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('password123')
            admin_user.save()

        # Customer
        customer_user, created = User.objects.get_or_create(
            username='customer',
            defaults={
                'email': 'customer@smartkart.ai',
                'first_name': 'Priya',
                'last_name': 'Sharma',
            }
        )
        if created:
            customer_user.set_password('password123')
            customer_user.save()

        # Customer Profile
        cust_profile, _ = CustomerProfile.objects.get_or_create(
            user=customer_user,
            defaults={
                'phone': '9876543210',
                'monthly_budget': Decimal('6000.00'),
                'budget_warning_threshold': 80,
                'budget_reset_day': 1,
            }
        )

        # Addresses for Customer
        addr1, _ = Address.objects.get_or_create(
            user=customer_user,
            full_name='Priya Sharma',
            phone_number='9876543210',
            address_type='HOME',
            street_address='Flat 402, Lotus Greens Apartments, Sector 15',
            landmark='Opposite City Central Park',
            city='New Delhi',
            state='Delhi',
            postal_code='110001',
            is_default=True
        )
        addr2, _ = Address.objects.get_or_create(
            user=customer_user,
            full_name='Priya Sharma (Office)',
            phone_number='9876543210',
            address_type='WORK',
            street_address='Tower B, 7th Floor, Cyber Tech Hub, Phase 2',
            landmark='Near Metro Station Gate 3',
            city='New Delhi',
            state='Delhi',
            postal_code='110020',
            is_default=False
        )

        # Delivery Personnel
        delivery_user, created = User.objects.get_or_create(
            username='delivery',
            defaults={
                'email': 'delivery@smartkart.ai',
                'first_name': 'Rahul',
                'last_name': 'Verma',
            }
        )
        if created:
            delivery_user.set_password('password123')
            delivery_user.save()

        deliv_profile, _ = DeliveryProfile.objects.get_or_create(
            user=delivery_user,
            defaults={
                'phone': '9812345678',
                'vehicle_type': 'Electric Scooter (EV)',
                'vehicle_number': 'DL 01 EV 4421',
                'driving_license': 'DL-0120220019283',
                'is_available': True,
                'is_approved': True,
                'rating': Decimal('4.90'),
                'total_deliveries': 38,
            }
        )

        # 2. Create Categories
        self.stdout.write("Creating categories...")
        categories_data = [
            ('Fruits & Vegetables', 'fruits-vegetables', 'bi-apple', 'Farm fresh daily greens, seasonal fruits and crunchy vegetables', 1),
            ('Dairy & Breakfast', 'dairy-breakfast', 'bi-egg-fried', 'Fresh pasteurized milk, paneer, butter, curd, bread and eggs', 2),
            ('Staples & Grains', 'staples-grains', 'bi-basket', 'Aashirvaad atta, aromatic basmati rice, pulses, and organic spices', 3),
            ('Snacks & Munchies', 'snacks-munchies', 'bi-cookie', 'Crispy namkeens, chips, roasted nuts, biscuits and treats', 4),
            ('Cold Drinks & Juices', 'cold-drinks-juices', 'bi-cup-straw', 'Chilled juices, soft drinks, tender coconut water and mixers', 5),
            ('Instant & Packaged Food', 'instant-packaged-food', 'bi-box-seam', 'Maggi noodles, pasta, ready-to-eat curries, soups and sauces', 6),
            ('Household Care', 'household-care', 'bi-house-heart', 'Detergents, dishwashing liquids, surface cleaners and tissues', 7),
            ('Personal Care', 'personal-care', 'bi-person-heart', 'Soaps, shampoos, oral care, handwash and skin moisturizers', 8),
        ]
        cat_map = {}
        for name, slug, icon, desc, order in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slug, 'icon_class': icon, 'description': desc, 'display_order': order}
            )
            cat_map[slug] = cat

        # 3. Create Brands
        self.stdout.write("Creating brands...")
        brands_data = [
            ('Amul', 'amul', 'The Taste of India dairy products'),
            ('Mother Dairy', 'mother-dairy', 'Fresh milk, curd and ice creams'),
            ('Fortune', 'fortune', 'Refined oils, basmati rice and soya chunks'),
            ('Tata Sampann', 'tata-sampann', 'Unpolished pulses, spices and poha'),
            ('Aashirvaad', 'aashirvaad', 'Whole wheat atta and organic flours'),
            ('Britannia', 'britannia', 'Breads, rusks, biscuits and cakes'),
            ('Tropicana', 'tropicana', '100% real fruit juices'),
            ('Surf Excel', 'surf-excel', 'Premium laundry detergents'),
        ]
        brand_map = {}
        for name, slug, desc in brands_data:
            brand, _ = Brand.objects.get_or_create(name=name, defaults={'slug': slug, 'description': desc})
            brand_map[slug] = brand

        # 4. Create Products
        self.stdout.write("Creating 45+ realistic Indian grocery products...")
        today = timezone.now().date()
        
        products_data = [
            # Fruits & Vegetables
            {
                'name': 'Fresh Hybrid Tomatoes', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Locally harvested firm red hybrid tomatoes perfect for Indian curries, gravies, and salads.',
                'orig': '40.00', 'sell': '32.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 45,
                'exp': today + datetime.timedelta(days=6), 'tags': 'Fresh, Farm Harvest, Antioxidant Rich', 'feat': True
            },
            {
                'name': 'Fresh Red Onions (Pyaz)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Pungent, crispy Nashik red onions essential for daily Indian cooking and tadka.',
                'orig': '45.00', 'sell': '35.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 60,
                'exp': today + datetime.timedelta(days=15), 'tags': 'Staple, Farm Direct', 'feat': True
            },
            {
                'name': 'Fresh Jyoti Potatoes (Aloo)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Grade-A smooth Jyoti potatoes with thin skins, ideal for frying, boiling, and curries.',
                'orig': '35.00', 'sell': '28.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 50,
                'exp': today + datetime.timedelta(days=20), 'tags': 'Carb Rich, Daily Essential', 'feat': False
            },
            {
                'name': 'Fresh Organic Coriander (Dhaniya)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Aromatic green coriander leaves with tender stems for garnishing curries and making chutneys.',
                'orig': '20.00', 'sell': '15.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 30,
                'exp': today + datetime.timedelta(days=3), 'tags': 'Organic, Fresh Herbs, Detox', 'feat': False
            },
            {
                'name': 'Fresh Green Chillies (Hari Mirch)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Crisp, spicy green chillies rich in Vitamin C, perfect for authentic Indian spices.',
                'orig': '25.00', 'sell': '18.00', 'unit': '200 g', 'uval': '0.2', 'utype': 'g', 'stock': 25,
                'exp': today + datetime.timedelta(days=7), 'tags': 'Spicy, Vitamin C Rich', 'feat': False
            },
            {
                'name': 'Fresh Ginger (Adrak)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Juicy, fibrous ginger root perfect for Indian chai, marinades, and tadka pastes.',
                'orig': '40.00', 'sell': '30.00', 'unit': '250 g', 'uval': '0.25', 'utype': 'g', 'stock': 20,
                'exp': today + datetime.timedelta(days=10), 'tags': 'Immunity Booster, Digestive', 'feat': False
            },
            {
                'name': 'Farm Fresh Garlic (Lehsun)', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Aromatic, single-clove and multi-clove white garlic with intense flavor.',
                'orig': '60.00', 'sell': '48.00', 'unit': '250 g', 'uval': '0.25', 'utype': 'g', 'stock': 22,
                'exp': today + datetime.timedelta(days=30), 'tags': 'Heart Healthy, Essential Spice', 'feat': False
            },
            {
                'name': 'Fresh Organic Strawberries Box', 'cat': 'fruits-vegetables', 'brand': None,
                'desc': 'Sweet, juicy Mahabaleshwar strawberries packed with antioxidants and Vitamin C.',
                'orig': '120.00', 'sell': '60.00', 'unit': '250 g', 'uval': '0.25', 'utype': 'g', 'stock': 12,
                'exp': today + datetime.timedelta(days=2), 'tags': 'Organic, Antioxidant, Sweet', 'feat': True
            },

            # Dairy & Breakfast
            {
                'name': 'Amul Taaza Homogenised Toned Milk', 'cat': 'dairy-breakfast', 'brand': 'amul',
                'desc': 'Pasteurized toned milk with 3.0% fat and 8.5% SNF. Wholesome and nutritious for daily tea and coffee.',
                'orig': '32.00', 'sell': '30.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 80,
                'exp': today + datetime.timedelta(days=2), 'tags': 'Calcium Rich, Low Fat, Daily Staple', 'feat': True
            },
            {
                'name': 'Amul Gold Full Cream Milk', 'cat': 'dairy-breakfast', 'brand': 'amul',
                'desc': 'Rich, creamy full cream pasteurized milk with 6.0% fat, ideal for making rich desserts and thick tea.',
                'orig': '36.00', 'sell': '34.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 70,
                'exp': today + datetime.timedelta(days=2), 'tags': 'Full Cream, High Energy, Protein', 'feat': True
            },
            {
                'name': 'Amul Pasteurized Salted Butter', 'cat': 'dairy-breakfast', 'brand': 'amul',
                'desc': 'Utterly butterly delicious butter made from pure milk fat. Adds rich flavor to toasts, parathas, and curries.',
                'orig': '60.00', 'sell': '56.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 40,
                'exp': today + datetime.timedelta(days=60), 'tags': 'Rich Dairy, Salted Butter', 'feat': True
            },
            {
                'name': 'Mother Dairy Fresh Paneer', 'cat': 'dairy-breakfast', 'brand': 'mother-dairy',
                'desc': 'Soft, spongy malai cottage cheese cubes packed with pure dairy protein for Paneer Butter Masala.',
                'orig': '95.00', 'sell': '85.00', 'unit': '200 g', 'uval': '0.2', 'utype': 'g', 'stock': 15,
                'exp': today + datetime.timedelta(days=1), 'tags': 'High Protein, Fresh Dairy, Vegetarian', 'feat': True
            },
            {
                'name': 'Mother Dairy Classic Dahi (Curd)', 'cat': 'dairy-breakfast', 'brand': 'mother-dairy',
                'desc': 'Thick and creamy curd made from pasteurized toned milk, rich in natural probiotics.',
                'orig': '40.00', 'sell': '35.00', 'unit': '400 g', 'uval': '0.4', 'utype': 'g', 'stock': 35,
                'exp': today + datetime.timedelta(days=4), 'tags': 'Probiotic, Gut Healthy, Calcium', 'feat': False
            },
            {
                'name': 'Britannia 100% Whole Wheat Brown Bread', 'cat': 'dairy-breakfast', 'brand': 'britannia',
                'desc': 'Wholesome brown bread baked with 100% whole wheat grains, loaded with natural dietary fiber.',
                'orig': '55.00', 'sell': '48.00', 'unit': '400 g', 'uval': '0.4', 'utype': 'g', 'stock': 28,
                'exp': today + datetime.timedelta(days=3), 'tags': 'High Fiber, Whole Wheat, Healthy Breakfast', 'feat': True
            },
            {
                'name': 'Farm Fresh White Eggs Tray (6 Eggs)', 'cat': 'dairy-breakfast', 'brand': None,
                'desc': 'Hygienically sorted and cleaned farm-fresh white eggs with high natural protein content.',
                'orig': '55.00', 'sell': '45.00', 'unit': '6 pcs', 'uval': '6.0', 'utype': 'pack', 'stock': 50,
                'exp': today + datetime.timedelta(days=14), 'tags': 'High Protein, Farm Fresh, Eggetarian', 'feat': True
            },
            {
                'name': 'Mother Dairy Greek Yogurt Blueberry', 'cat': 'dairy-breakfast', 'brand': 'mother-dairy',
                'desc': 'Deliciously thick, strained Greek yogurt infused with real blueberries and high protein.',
                'orig': '60.00', 'sell': '30.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 8,
                'exp': today + datetime.timedelta(days=2), 'tags': 'High Protein, Greek Yogurt, Probiotic', 'feat': False
            },

            # Staples & Grains
            {
                'name': 'Aashirvaad Shudh Chakki Whole Wheat Atta', 'cat': 'staples-grains', 'brand': 'aashirvaad',
                'desc': 'Made from 100% MP Sharbati whole wheat grains. Makes soft, fluffy rotis with high dietary fiber.',
                'orig': '260.00', 'sell': '235.00', 'unit': '5 kg', 'uval': '5.0', 'utype': 'kg', 'stock': 40,
                'exp': today + datetime.timedelta(days=120), 'tags': '100% Whole Wheat, High Fiber, Staple', 'feat': True
            },
            {
                'name': 'Fortune Everyday Basmati Rice', 'cat': 'staples-grains', 'brand': 'fortune',
                'desc': 'Long grain, aromatic basmati rice aged to perfection for everyday pulao, biryani, and steamed rice.',
                'orig': '140.00', 'sell': '115.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 35,
                'exp': today + datetime.timedelta(days=300), 'tags': 'Aromatic Basmati, Long Grain', 'feat': True
            },
            {
                'name': 'Tata Sampann Unpolished Toor Dal (Arhar)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Unpolished yellow pigeon peas rich in natural plant protein and wholesome dietary nutrients.',
                'orig': '180.00', 'sell': '155.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 30,
                'exp': today + datetime.timedelta(days=180), 'tags': 'Unpolished, High Protein, Gluten Free', 'feat': True
            },
            {
                'name': 'Tata Sampann Unpolished Moong Dal', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Split yellow mung beans that cook quickly into light, easily digestible comfort dal.',
                'orig': '165.00', 'sell': '140.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 25,
                'exp': today + datetime.timedelta(days=180), 'tags': 'Easy Digest, High Protein', 'feat': False
            },
            {
                'name': 'Tata Sampann Kabuli Chana (Chickpeas)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Large-grain premium white chickpeas for Punjabi Chole Masala and Mediterranean hummus.',
                'orig': '170.00', 'sell': '145.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 30,
                'exp': today + datetime.timedelta(days=200), 'tags': 'High Protein, Rich in Fiber', 'feat': True
            },
            {
                'name': 'Fortune Sunlite Refined Sunflower Oil', 'cat': 'staples-grains', 'brand': 'fortune',
                'desc': 'Light and healthy refined sunflower oil enriched with Vitamin A and Vitamin D for heart health.',
                'orig': '165.00', 'sell': '139.00', 'unit': '1 L', 'uval': '1.0', 'utype': 'l', 'stock': 45,
                'exp': today + datetime.timedelta(days=240), 'tags': 'Heart Healthy, Enriched Vitamins', 'feat': True
            },
            {
                'name': 'Tata Salt Vacuum Evaporated Iodized Salt', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Desh ka Namak - pure vacuum evaporated iodized table salt essential for daily seasoning.',
                'orig': '28.00', 'sell': '25.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 100,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Iodized, Daily Essential', 'feat': False
            },
            {
                'name': 'Tata Sampann Thick Poha (Beaten Rice)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'High-fiber thick flattened rice flakes for making authentic Maharashtrian breakfast Kanda Poha.',
                'orig': '65.00', 'sell': '52.00', 'unit': '500 g', 'uval': '0.5', 'utype': 'g', 'stock': 35,
                'exp': today + datetime.timedelta(days=150), 'tags': 'Iron Rich, Low Calorie, Quick Cook', 'feat': True
            },
            {
                'name': 'Madhur Pure & Hygienic Sugar', 'cat': 'staples-grains', 'brand': None,
                'desc': '100% sulphur-free refined white sparkling sugar crystals for beverages and sweet delicacies.',
                'orig': '55.00', 'sell': '46.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 50,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Sulphur Free, Refined Sugar', 'feat': False
            },
            {
                'name': 'Tata Sampann Premium Mustard Seeds (Rai)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Aromatic black mustard seeds with intense pungent aroma, ideal for South Indian and Gujarati tadka.',
                'orig': '45.00', 'sell': '38.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 25,
                'exp': today + datetime.timedelta(days=200), 'tags': 'Spices, Tadka Essential', 'feat': False
            },
            {
                'name': 'Tata Sampann Cumin Seeds (Jeera)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Whole aromatic cumin seeds with rich essential oils for tempering Dal Tadka and curries.',
                'orig': '80.00', 'sell': '65.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 30,
                'exp': today + datetime.timedelta(days=200), 'tags': 'Digestive, Aromatic Spice', 'feat': False
            },
            {
                'name': 'Tata Sampann Turmeric Powder (Haldi)', 'cat': 'staples-grains', 'brand': 'tata-sampann',
                'desc': 'Pure turmeric powder with guaranteed 3% natural curcumin content for golden color and immunity.',
                'orig': '42.00', 'sell': '35.00', 'unit': '100 g', 'uval': '0.1', 'utype': 'g', 'stock': 40,
                'exp': today + datetime.timedelta(days=250), 'tags': 'High Curcumin, Immunity Booster', 'feat': False
            },

            # Snacks & Munchies
            {
                'name': 'Haldirams Classic Bhujia Sev', 'cat': 'snacks-munchies', 'brand': None,
                'desc': 'Crispy, spicy moth bean and gram flour strings seasoned with authentic Rajasthani spices.',
                'orig': '110.00', 'sell': '95.00', 'unit': '400 g', 'uval': '0.4', 'utype': 'g', 'stock': 35,
                'exp': today + datetime.timedelta(days=90), 'tags': 'Spicy Namkeen, Tea Time Snack', 'feat': True
            },
            {
                'name': 'Britannia Good Day Butter Cookies', 'cat': 'snacks-munchies', 'brand': 'britannia',
                'desc': 'Rich butter cookies with a delightful smile texture, perfect companion for evening tea.',
                'orig': '40.00', 'sell': '32.00', 'unit': '200 g', 'uval': '0.2', 'utype': 'g', 'stock': 45,
                'exp': today + datetime.timedelta(days=120), 'tags': 'Butter Cookies, Sweet Snack', 'feat': True
            },
            {
                'name': 'Lays India Magic Masala Chips', 'cat': 'snacks-munchies', 'brand': None,
                'desc': 'Crispy ridged potato chips infused with a rich blend of spicy Indian herbs and spices.',
                'orig': '20.00', 'sell': '18.00', 'unit': '50 g', 'uval': '0.05', 'utype': 'g', 'stock': 60,
                'exp': today + datetime.timedelta(days=60), 'tags': 'Crispy Chips, Spicy Masala', 'feat': False
            },
            {
                'name': 'Roasted Salted California Almonds (Badam)', 'cat': 'snacks-munchies', 'brand': None,
                'desc': 'Crunchy, lightly salted California almonds packed with Vitamin E and healthy omega fats.',
                'orig': '240.00', 'sell': '199.00', 'unit': '200 g', 'uval': '0.2', 'utype': 'g', 'stock': 25,
                'exp': today + datetime.timedelta(days=150), 'tags': 'Superfood, Healthy Fats, Protein', 'feat': True
            },

            # Cold Drinks & Juices
            {
                'name': 'Tropicana 100% Real Orange Juice', 'cat': 'cold-drinks-juices', 'brand': 'tropicana',
                'desc': 'Refreshing 100% natural orange juice with no added sugar or preservatives. Rich in Vitamin C.',
                'orig': '135.00', 'sell': '115.00', 'unit': '1 L', 'uval': '1.0', 'utype': 'l', 'stock': 30,
                'exp': today + datetime.timedelta(days=90), 'tags': 'No Added Sugar, Vitamin C, 100% Juice', 'feat': True
            },
            {
                'name': 'Coca-Cola Zero Sugar Can', 'cat': 'cold-drinks-juices', 'brand': None,
                'desc': 'Classic refreshing Coca-Cola taste with zero calories and zero sugar.',
                'orig': '40.00', 'sell': '35.00', 'unit': '300 ml', 'uval': '0.3', 'utype': 'l', 'stock': 40,
                'exp': today + datetime.timedelta(days=120), 'tags': 'Zero Sugar, Calorie Free', 'feat': False
            },
            {
                'name': 'Fresh Tender Coconut Water Bottle', 'cat': 'cold-drinks-juices', 'brand': None,
                'desc': 'Pure, naturally refreshing coconut water packed with natural electrolytes and potassium.',
                'orig': '65.00', 'sell': '55.00', 'unit': '200 ml', 'uval': '0.2', 'utype': 'l', 'stock': 25,
                'exp': today + datetime.timedelta(days=45), 'tags': 'Electrolytes, Natural Hydration', 'feat': True
            },

            # Instant & Packaged Food
            {
                'name': 'Nestle Maggi 2-Minute Masala Noodles Pack of 4', 'cat': 'instant-packaged-food', 'brand': None,
                'desc': 'The iconic Indian comfort snack made with quality spices and fortified with Vitamin A and Iron.',
                'orig': '60.00', 'sell': '54.00', 'unit': '280 g', 'uval': '0.28', 'utype': 'g', 'stock': 70,
                'exp': today + datetime.timedelta(days=180), 'tags': 'Quick Cook, Comfort Food', 'feat': True
            },
            {
                'name': 'Borges Durum Wheat Penne Rigate Pasta', 'cat': 'instant-packaged-food', 'brand': None,
                'desc': 'Authentic 100% Italian durum wheat semolina penne pasta that holds sauces perfectly.',
                'orig': '150.00', 'sell': '125.00', 'unit': '500 g', 'uval': '0.5', 'utype': 'g', 'stock': 30,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Durum Wheat, High Fiber, Italian', 'feat': True
            },
            {
                'name': 'Kissan Fresh Tomato Ketchup Bottle', 'cat': 'instant-packaged-food', 'brand': None,
                'desc': 'Made from 100% real ripe tomatoes. Tangy, sweet ketchup pairing with snacks and sandwiches.',
                'orig': '130.00', 'sell': '110.00', 'unit': '950 g', 'uval': '0.95', 'utype': 'g', 'stock': 35,
                'exp': today + datetime.timedelta(days=200), 'tags': 'Real Tomatoes, Condiment', 'feat': False
            },
            {
                'name': 'Veeba Eggless Mayonnaise Classic', 'cat': 'instant-packaged-food', 'brand': None,
                'desc': 'Thick and creamy 100% vegetarian mayonnaise for burgers, rolls, and sandwiches.',
                'orig': '99.00', 'sell': '85.00', 'unit': '250 g', 'uval': '0.25', 'utype': 'g', 'stock': 25,
                'exp': today + datetime.timedelta(days=120), 'tags': 'Eggless, Creamy Dip, Vegetarian', 'feat': False
            },

            # Household Care
            {
                'name': 'Surf Excel Matic Front Load Detergent Powder', 'cat': 'household-care', 'brand': 'surf-excel',
                'desc': 'Engineered to produce the right amount of foam for front load washing machines and tough stain removal.',
                'orig': '250.00', 'sell': '215.00', 'unit': '1 kg', 'uval': '1.0', 'utype': 'kg', 'stock': 30,
                'exp': today + datetime.timedelta(days=500), 'tags': 'Tough Stain Removal, Washing Machine', 'feat': True
            },
            {
                'name': 'Vim Lemon Dishwash Liquid Gel', 'cat': 'household-care', 'brand': None,
                'desc': 'Concentrated dishwashing gel with the power of 100 lemons to cut through grease effortlessly.',
                'orig': '120.00', 'sell': '102.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 40,
                'exp': today + datetime.timedelta(days=500), 'tags': 'Grease Removal, Lemon Fresh', 'feat': True
            },
            {
                'name': 'Lizol Citrus Floor Cleaner Disinfectant', 'cat': 'household-care', 'brand': None,
                'desc': 'Kills 99.9% of germs and viruses while leaving behind a sparkling shine and citrus fragrance.',
                'orig': '115.00', 'sell': '99.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 35,
                'exp': today + datetime.timedelta(days=500), 'tags': 'Disinfectant, Germ Kill', 'feat': False
            },

            # Personal Care
            {
                'name': 'Dettol Original Germ Protection Liquid Handwash', 'cat': 'personal-care', 'brand': None,
                'desc': 'pH-balanced liquid handwash with trusted Dettol pine fragrance for 99.9% germ protection.',
                'orig': '99.00', 'sell': '85.00', 'unit': '200 ml', 'uval': '0.2', 'utype': 'l', 'stock': 45,
                'exp': today + datetime.timedelta(days=400), 'tags': 'Germ Protection, pH Balanced', 'feat': True
            },
            {
                'name': 'Colgate Total Advanced Health Toothpaste', 'cat': 'personal-care', 'brand': None,
                'desc': 'Antibacterial toothpaste providing 12-hour whole mouth protection against plaque and cavities.',
                'orig': '120.00', 'sell': '105.00', 'unit': '120 g', 'uval': '0.12', 'utype': 'g', 'stock': 50,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Antibacterial, Oral Care', 'feat': False
            },

            # Out of Stock Items specifically for Smart Substitution testing
            {
                'name': 'Organic Cow Ghee Glass Jar (Premium)', 'cat': 'dairy-breakfast', 'brand': 'amul',
                'desc': 'Traditional bilona method pure cow ghee with golden granules and divine aroma.',
                'orig': '650.00', 'sell': '580.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 0, # OUT OF STOCK
                'exp': today + datetime.timedelta(days=180), 'tags': 'Pure Ghee, Organic, High Aroma', 'feat': False
            },
            {
                'name': 'Amul Pure Desi Ghee Carton Pack', 'cat': 'dairy-breakfast', 'brand': 'amul',
                'desc': 'Wholesome clarified butter fat made from fresh cream. Essential for sweets, dal, and parathas.',
                'orig': '320.00', 'sell': '290.00', 'unit': '500 ml', 'uval': '0.5', 'utype': 'l', 'stock': 25, # IN STOCK SUBSTITUTE
                'exp': today + datetime.timedelta(days=180), 'tags': 'Pure Ghee, Desi Ghee, Traditional', 'feat': True
            },
            {
                'name': 'Wagh Bakri Premium CTC Tea (Chai)', 'cat': 'beverages' if 'beverages' in cat_map else 'cold-drinks-juices', 'brand': None,
                'desc': 'Strong blend of Assam tea leaves delivering rich liquor, robust aroma, and authentic taste.',
                'orig': '160.00', 'sell': '135.00', 'unit': '500 g', 'uval': '0.5', 'utype': 'g', 'stock': 35,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Strong Tea, CTC Blend, Kadak Chai', 'feat': True
            },
            {
                'name': 'Tata Tea Gold Premium Assam Leaves', 'cat': 'beverages' if 'beverages' in cat_map else 'cold-drinks-juices', 'brand': None,
                'desc': 'Exquisite blend of CTC tea and gently rolled long tea leaves for irresistible aroma.',
                'orig': '175.00', 'sell': '148.00', 'unit': '500 g', 'uval': '0.5', 'utype': 'g', 'stock': 30,
                'exp': today + datetime.timedelta(days=365), 'tags': 'Assam Tea, Aromatic, Premium Chai', 'feat': True
            },
        ]

        prod_map = {}
        for p in products_data:
            cat_obj = cat_map.get(p['cat']) or cat_map['staples-grains']
            brand_obj = brand_map.get(p['brand']) if p['brand'] else None

            prod, created = Product.objects.get_or_create(
                name=p['name'],
                defaults={
                    'category': cat_obj,
                    'brand': brand_obj,
                    'description': p['desc'],
                    'original_price': Decimal(p['orig']),
                    'selling_price': Decimal(p['sell']),
                    'unit': p['unit'],
                    'unit_value': Decimal(p['uval']),
                    'unit_type': p['utype'],
                    'stock_quantity': p['stock'],
                    'reorder_level': 10,
                    'expiry_date': p['exp'],
                    'nutritional_tags': p['tags'],
                    'is_featured': p['feat'],
                    'is_active': True,
                    'average_rating': Decimal('4.80') if p['feat'] else Decimal('4.50'),
                    'total_reviews': 12 if p['feat'] else 4,
                }
            )
            if not created and refresh_dates and prod.expiry_date != p['exp']:
                prod.expiry_date = p['exp']
                prod.save(update_fields=['expiry_date'])
            prod_map[p['name']] = prod

        # 5. Create 8 Curated Recipes
        self.stdout.write("Creating 8 Indian & International Recipes with mapped ingredients...")
        recipes_data = [
            {
                'name': 'Paneer Butter Masala',
                'cuisine': 'North Indian',
                'diet': 'VEG',
                'prep': 15, 'cook': 25, 'servings': 4, 'diff': 'MEDIUM', 'feat': True,
                'desc': 'Rich, creamy and mildly sweet restaurant-style curry made with fresh paneer, butter, and silky tomato gravy.',
                'instructions': '1. Heat 2 tbsp butter in a pan and saute ginger-garlic paste with green chillies.\n2. Add pureed tomatoes, salt, and turmeric powder. Cook till oil separates.\n3. Add fresh cubed paneer and simmer gently for 5 minutes.\n4. Finish with fresh cream and chopped coriander leaves. Serve hot with rotis or rice.',
                'ingredients': [
                    ('Mother Dairy Fresh Paneer', 'Fresh Paneer', Decimal('200.00'), 'g', False, 'cubed'),
                    ('Fresh Hybrid Tomatoes', 'Ripe Tomatoes', Decimal('400.00'), 'g', False, 'pureed'),
                    ('Amul Pasteurized Salted Butter', 'Butter', Decimal('50.00'), 'g', False, 'salted butter'),
                    ('Fresh Ginger (Adrak)', 'Ginger', Decimal('20.00'), 'g', False, 'finely minced'),
                    ('Tata Salt Vacuum Evaporated Iodized Salt', 'Iodized Salt', Decimal('5.00'), 'g', False, 'to taste'),
                    ('Tata Sampann Turmeric Powder (Haldi)', 'Turmeric Powder', Decimal('5.00'), 'g', False, 'ground'),
                    ('Fresh Organic Coriander (Dhaniya)', 'Fresh Coriander', Decimal('20.00'), 'g', False, 'chopped for garnish'),
                ]
            },
            {
                'name': 'Dal Tadka Restaurant Style',
                'cuisine': 'North Indian',
                'diet': 'VEG',
                'prep': 10, 'cook': 20, 'servings': 4, 'diff': 'EASY', 'feat': True,
                'desc': 'Aromatic yellow toor lentils tempered with sizzling ghee, cumin, garlic, and fresh green chillies.',
                'instructions': '1. Pressure cook washed Toor Dal with turmeric, salt, and water for 4 whistles.\n2. In a small pan, heat ghee or oil and add cumin seeds, chopped garlic, and green chillies.\n3. Add chopped onions and tomatoes; cook until soft.\n4. Pour the sizzling tadka over the boiled dal. Garnish with fresh coriander.',
                'ingredients': [
                    ('Tata Sampann Unpolished Toor Dal (Arhar)', 'Toor Dal (Arhar)', Decimal('200.00'), 'g', False, 'washed & soaked'),
                    ('Tata Sampann Cumin Seeds (Jeera)', 'Jeera (Cumin)', Decimal('5.00'), 'g', False, 'for tempering'),
                    ('Farm Fresh Garlic (Lehsun)', 'Garlic Cloves', Decimal('20.00'), 'g', False, 'finely sliced'),
                    ('Fresh Red Onions (Pyaz)', 'Red Onions', Decimal('100.00'), 'g', False, 'chopped'),
                    ('Fresh Hybrid Tomatoes', 'Tomatoes', Decimal('100.00'), 'g', False, 'chopped'),
                    ('Tata Salt Vacuum Evaporated Iodized Salt', 'Salt', Decimal('5.00'), 'g', False, 'to taste'),
                    ('Fresh Organic Coriander (Dhaniya)', 'Coriander Leaves', Decimal('15.00'), 'g', False, 'chopped'),
                ]
            },
            {
                'name': 'Authentic Kanda Poha',
                'cuisine': 'Maharashtrian',
                'diet': 'VEG',
                'prep': 10, 'cook': 15, 'servings': 4, 'diff': 'EASY', 'feat': True,
                'desc': 'Classic quick breakfast made of flattened beaten rice, caramelized onions, mustard seeds, and crunchy roasted peanuts.',
                'instructions': '1. Gently rinse poha in water and drain completely.\n2. Heat oil in a pan, crackle mustard seeds, and saute onions, green chillies, and potatoes.\n3. Add turmeric powder and salt.\n4. Mix in the softened poha gently. Steam for 2 minutes and garnish with fresh coriander.',
                'ingredients': [
                    ('Tata Sampann Thick Poha (Beaten Rice)', 'Thick Poha', Decimal('250.00'), 'g', False, 'rinsed and drained'),
                    ('Fresh Red Onions (Pyaz)', 'Red Onions', Decimal('150.00'), 'g', False, 'finely sliced'),
                    ('Fresh Jyoti Potatoes (Aloo)', 'Potatoes', Decimal('100.00'), 'g', False, 'small diced'),
                    ('Tata Sampann Premium Mustard Seeds (Rai)', 'Mustard Seeds (Rai)', Decimal('5.00'), 'g', False, 'for tadka'),
                    ('Tata Sampann Turmeric Powder (Haldi)', 'Turmeric', Decimal('3.00'), 'g', False, 'for vibrant color'),
                    ('Fresh Green Chillies (Hari Mirch)', 'Green Chillies', Decimal('10.00'), 'g', False, 'chopped'),
                    ('Fresh Organic Coriander (Dhaniya)', 'Fresh Coriander', Decimal('15.00'), 'g', False, 'garnish'),
                ]
            },
            {
                'name': 'Punjabi Chole Masala',
                'cuisine': 'North Indian',
                'diet': 'VEG',
                'prep': 20, 'cook': 35, 'servings': 4, 'diff': 'MEDIUM', 'feat': True,
                'desc': 'Zesty and tangy dark chickpeas cooked in a spicy onion-tomato gravy with roasted spices.',
                'instructions': '1. Soak chickpeas overnight and pressure cook with tea bag and salt.\n2. Heat oil, fry chopped onions, ginger-garlic paste till golden.\n3. Add tomato puree, turmeric, cumin, and chole spices.\n4. Add boiled chickpeas and simmer for 15 minutes. Serve with hot bhature or rice.',
                'ingredients': [
                    ('Tata Sampann Kabuli Chana (Chickpeas)', 'Kabuli Chana', Decimal('250.00'), 'g', False, 'soaked & boiled'),
                    ('Fresh Red Onions (Pyaz)', 'Onions', Decimal('200.00'), 'g', False, 'pureed'),
                    ('Fresh Hybrid Tomatoes', 'Tomatoes', Decimal('250.00'), 'g', False, 'pureed'),
                    ('Fresh Ginger (Adrak)', 'Ginger', Decimal('20.00'), 'g', False, 'julienned'),
                    ('Tata Sampann Cumin Seeds (Jeera)', 'Cumin Seeds', Decimal('5.00'), 'g', False, 'ground'),
                    ('Tata Salt Vacuum Evaporated Iodized Salt', 'Salt', Decimal('5.00'), 'g', False, 'to taste'),
                ]
            },
            {
                'name': 'Fragrant Vegetable Pulao',
                'cuisine': 'North Indian',
                'diet': 'VEG',
                'prep': 15, 'cook': 20, 'servings': 4, 'diff': 'EASY', 'feat': False,
                'desc': 'Aromatic one-pot rice dish loaded with crunchy veggies, cumin, and whole basmati rice.',
                'instructions': '1. Wash and soak basmati rice for 20 minutes.\n2. In a pot, heat oil, add cumin seeds, onions, potatoes, and tomatoes.\n3. Add rice, water, and salt.\n4. Cover and cook on low flame for 15 minutes until fluffy.',
                'ingredients': [
                    ('Fortune Everyday Basmati Rice', 'Basmati Rice', Decimal('300.00'), 'g', False, 'aged long grain'),
                    ('Fresh Red Onions (Pyaz)', 'Onions', Decimal('100.00'), 'g', False, 'sliced'),
                    ('Fresh Jyoti Potatoes (Aloo)', 'Potatoes', Decimal('150.00'), 'g', False, 'diced'),
                    ('Tata Sampann Cumin Seeds (Jeera)', 'Cumin', Decimal('5.00'), 'g', False, 'whole'),
                    ('Fortune Sunlite Refined Sunflower Oil', 'Sunflower Oil', Decimal('30.00'), 'ml', False, 'cooking oil'),
                    ('Tata Salt Vacuum Evaporated Iodized Salt', 'Salt', Decimal('5.00'), 'g', False, 'to taste'),
                ]
            },
            {
                'name': 'Classic Kadak Masala Chai',
                'cuisine': 'North Indian',
                'diet': 'VEG',
                'prep': 5, 'cook': 10, 'servings': 2, 'diff': 'EASY', 'feat': True,
                'desc': 'Invigorating Indian street-style spiced milk tea with crushed fresh ginger, cardamom, and strong Assam tea leaves.',
                'instructions': '1. Boil 1 cup water with crushed fresh ginger.\n2. Add 2 tsp strong tea leaves and simmer for 2 minutes.\n3. Add 1 cup whole milk and sugar. Bring to a rolling boil twice.\n4. Strain into cups and serve steaming hot.',
                'ingredients': [
                    ('Amul Taaza Homogenised Toned Milk', 'Fresh Milk', Decimal('250.00'), 'ml', False, 'pasteurized milk'),
                    ('Tata Tea Gold Premium Assam Leaves', 'Assam Tea Leaves', Decimal('15.00'), 'g', False, 'CTC blend'),
                    ('Fresh Ginger (Adrak)', 'Fresh Ginger', Decimal('15.00'), 'g', False, 'crushed'),
                    ('Madhur Pure & Hygienic Sugar', 'Sugar', Decimal('15.00'), 'g', False, 'sweetener'),
                ]
            },
            {
                'name': 'Veg Club Sandwich',
                'cuisine': 'Continental',
                'diet': 'VEG',
                'prep': 10, 'cook': 5, 'servings': 2, 'diff': 'EASY', 'feat': False,
                'desc': 'Triple-layered toasted whole wheat bread loaded with crisp cucumber, fresh tomato slices, butter, and mayonnaise.',
                'instructions': '1. Toast bread slices with butter on a tawa.\n2. Spread mayonnaise and ketchup on bread slices.\n3. Layer with sliced tomatoes, onions, and boiled potatoes.\n4. Cut diagonally and serve with chips.',
                'ingredients': [
                    ('Britannia 100% Whole Wheat Brown Bread', 'Brown Bread', Decimal('4.00'), 'piece', False, 'slices'),
                    ('Amul Pasteurized Salted Butter', 'Butter', Decimal('20.00'), 'g', False, 'for toasting'),
                    ('Fresh Hybrid Tomatoes', 'Tomatoes', Decimal('100.00'), 'g', False, 'sliced'),
                    ('Fresh Red Onions (Pyaz)', 'Onions', Decimal('50.00'), 'g', False, 'sliced'),
                    ('Veeba Eggless Mayonnaise Classic', 'Mayonnaise', Decimal('30.00'), 'g', False, 'spread'),
                    ('Kissan Fresh Tomato Ketchup Bottle', 'Tomato Ketchup', Decimal('20.00'), 'g', False, 'condiment'),
                ]
            },
            {
                'name': 'Creamy Tomato Penne Pasta',
                'cuisine': 'Italian',
                'diet': 'VEG',
                'prep': 10, 'cook': 15, 'servings': 3, 'diff': 'EASY', 'feat': False,
                'desc': 'Durum wheat penne tossed in rich homemade garlic-tomato concasse with butter and herbs.',
                'instructions': '1. Boil penne pasta in salted water till al dente. Drain.\n2. In a skillet, saute chopped garlic in butter and sunflower oil.\n3. Add fresh tomato puree, salt, and simmer until thick.\n4. Toss in boiled pasta and mix well.',
                'ingredients': [
                    ('Borges Durum Wheat Penne Rigate Pasta', 'Penne Pasta', Decimal('250.00'), 'g', False, 'durum wheat'),
                    ('Fresh Hybrid Tomatoes', 'Tomatoes', Decimal('300.00'), 'g', False, 'pureed'),
                    ('Farm Fresh Garlic (Lehsun)', 'Garlic', Decimal('15.00'), 'g', False, 'minced'),
                    ('Amul Pasteurized Salted Butter', 'Butter', Decimal('30.00'), 'g', False, 'sauce base'),
                    ('Tata Salt Vacuum Evaporated Iodized Salt', 'Salt', Decimal('5.00'), 'g', False, 'to taste'),
                ]
            },
        ]

        for r_data in recipes_data:
            recipe, _ = Recipe.objects.get_or_create(
                name=r_data['name'],
                defaults={
                    'cuisine': r_data['cuisine'],
                    'diet_type': r_data['diet'],
                    'prep_time_minutes': r_data['prep'],
                    'cook_time_minutes': r_data['cook'],
                    'base_servings': r_data['servings'],
                    'difficulty': r_data['diff'],
                    'description': r_data['desc'],
                    'instructions': r_data['instructions'],
                    'is_featured': r_data['feat'],
                }
            )

            # Map ingredients
            for prod_name, ing_name, qty, unit, opt, notes in r_data['ingredients']:
                matched_p = prod_map.get(prod_name)
                RecipeIngredient.objects.get_or_create(
                    recipe=recipe,
                    ingredient_name=ing_name,
                    defaults={
                        'product': matched_p,
                        'quantity_per_base_servings': qty,
                        'unit': unit,
                        'is_optional': opt,
                        'notes': notes,
                    }
                )

        # 6. Create Coupons
        self.stdout.write("Creating coupons...")
        coupons_list = [
            ('WELCOME50', 'Welcome ₹50 Flat Discount for New Shoppers', 'FLAT', Decimal('50.00'), Decimal('299.00'), None, 500),
            ('SMARTKART100', 'Flat ₹100 Off on Household Orders above ₹599', 'FLAT', Decimal('100.00'), Decimal('599.00'), None, 1000),
            ('SUPER20', '20% Off Mega Savings on Groceries', 'PERCENT', Decimal('20.00'), Decimal('499.00'), Decimal('150.00'), 500),
            ('FREEDEL', 'Free Express 15-Min Delivery on Any Order', 'FLAT', Decimal('30.00'), Decimal('199.00'), None, 2000),
        ]
        for code, desc, dtype, dval, min_val, max_d, limit in coupons_list:
            Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'description': desc,
                    'discount_type': dtype,
                    'discount_value': dval,
                    'min_order_value': min_val,
                    'max_discount': max_d,
                    'valid_to': timezone.now() + timezone.timedelta(days=90),
                    'usage_limit': limit,
                    'is_active': True,
                }
            )

        # 7. Create Expiry Rescue Deals
        self.stdout.write("Creating active Expiry Rescue Deals...")
        rescue_items = [
            ('Mother Dairy Fresh Paneer', 60, today + datetime.timedelta(days=1)),
            ('Mother Dairy Greek Yogurt Blueberry', 50, today + datetime.timedelta(days=2)),
            ('Fresh Organic Strawberries Box', 50, today + datetime.timedelta(days=2)),
            ('Britannia 100% Whole Wheat Brown Bread', 45, today + datetime.timedelta(days=3)),
        ]
        for prod_name, discount_pct, exp_d in rescue_items:
            prod_obj = prod_map.get(prod_name)
            if prod_obj:
                ExpiryRescueDeal.objects.update_or_create(
                    product=prod_obj,
                    defaults={
                        'rescue_discount_percent': discount_pct,
                        'rescue_price': (prod_obj.original_price * (Decimal('1.00') - (Decimal(str(discount_pct)) / Decimal('100.00')))).quantize(Decimal('0.01')),
                        'expiry_date': exp_d,
                        'start_date': today,
                        'end_date': exp_d,
                        'is_active': True,
                        'rescued_count': 14,
                    }
                )

        # 8. Create Sample Monthly Budget
        now = timezone.now()
        MonthlyBudget.objects.get_or_create(
            user=customer_user,
            month=now.month,
            year=now.year,
            defaults={
                'budget_amount': Decimal('6000.00'),
                'warning_threshold_percent': 80,
                'notes': 'Family Monthly Grocery Budget'
            }
        )

        # 9. Create Sample Orders & Status Histories
        self.stdout.write("Creating sample customer orders...")
        
        # Order 1: Delivered
        if not Order.objects.filter(user=customer_user).exists():
            ord1 = Order.objects.create(
                user=customer_user,
                status='DELIVERED',
                shipping_full_name='Priya Sharma',
                shipping_phone='9876543210',
                shipping_street='Flat 402, Lotus Greens Apartments, Sector 15',
                shipping_landmark='Opposite City Central Park',
                shipping_city='New Delhi',
                shipping_state='Delhi',
                shipping_postal_code='110001',
                delivery_slot='EXPRESS_15MIN',
                subtotal=Decimal('420.00'),
                product_discount=Decimal('60.00'),
                coupon_code='WELCOME50',
                coupon_discount=Decimal('50.00'),
                delivery_fee=Decimal('0.00'),
                grand_total=Decimal('310.00'),
                payment_method='UPI',
                payment_status='PAID',
                transaction_id='TXN-DEMOUPI991',
                delivery_partner=delivery_user,
                delivered_at=now - timezone.timedelta(days=2)
            )
            OrderItem.objects.create(
                order=ord1,
                product=prod_map.get('Aashirvaad Shudh Chakki Whole Wheat Atta'),
                product_name='Aashirvaad Shudh Chakki Whole Wheat Atta',
                product_unit='5 kg',
                unit_price=Decimal('235.00'),
                original_price=Decimal('260.00'),
                quantity=1,
                total_price=Decimal('235.00'),
            )
            OrderItem.objects.create(
                order=ord1,
                product=prod_map.get('Fortune Everyday Basmati Rice'),
                product_name='Fortune Everyday Basmati Rice',
                product_unit='1 kg',
                unit_price=Decimal('115.00'),
                original_price=Decimal('140.00'),
                quantity=1,
                total_price=Decimal('115.00'),
            )
            OrderStatusHistory.objects.create(order=ord1, status='PLACED', comment="Order placed by customer.")
            OrderStatusHistory.objects.create(order=ord1, status='CONFIRMED', comment="Confirmed by Store Hub.")
            OrderStatusHistory.objects.create(order=ord1, status='PICKED_UP', comment="Picked up by rider Rahul Verma.")
            OrderStatusHistory.objects.create(order=ord1, status='DELIVERED', comment="Delivered to doorstep.")

            # Sample Verified Review
            Review.objects.create(
                product=prod_map.get('Aashirvaad Shudh Chakki Whole Wheat Atta'),
                user=customer_user,
                order=ord1,
                rating=5,
                headline="Soft and fluffy rotis, 15 min super fast delivery!",
                comment="Authentic fresh atta delivered in less than 20 minutes. Very impressed with the quick turnaround.",
                is_verified_purchase=True
            )

            # Order 2: Out for Delivery
            ord2 = Order.objects.create(
                user=customer_user,
                status='OUT_FOR_DELIVERY',
                shipping_full_name='Priya Sharma',
                shipping_phone='9876543210',
                shipping_street='Flat 402, Lotus Greens Apartments, Sector 15',
                shipping_landmark='Opposite City Central Park',
                shipping_city='New Delhi',
                shipping_state='Delhi',
                shipping_postal_code='110001',
                delivery_slot='EXPRESS_15MIN',
                subtotal=Decimal('255.00'),
                product_discount=Decimal('25.00'),
                coupon_code='',
                coupon_discount=Decimal('0.00'),
                delivery_fee=Decimal('30.00'),
                grand_total=Decimal('285.00'),
                payment_method='COD',
                payment_status='PENDING',
                delivery_partner=delivery_user,
            )
            OrderItem.objects.create(
                order=ord2,
                product=prod_map.get('Mother Dairy Fresh Paneer'),
                product_name='Mother Dairy Fresh Paneer',
                product_unit='200 g',
                unit_price=Decimal('85.00'),
                original_price=Decimal('95.00'),
                quantity=2,
                total_price=Decimal('170.00'),
            )
            OrderItem.objects.create(
                order=ord2,
                product=prod_map.get('Amul Pasteurized Salted Butter'),
                product_name='Amul Pasteurized Salted Butter',
                product_unit='100 g',
                unit_price=Decimal('56.00'),
                original_price=Decimal('60.00'),
                quantity=1,
                total_price=Decimal('56.00'),
            )
            OrderStatusHistory.objects.create(order=ord2, status='PLACED', comment="Order placed.")
            OrderStatusHistory.objects.create(order=ord2, status='ASSIGNED', comment="Assigned to rider Rahul Verma.")
            OrderStatusHistory.objects.create(order=ord2, status='OUT_FOR_DELIVERY', comment="Rider on the road to destination.")

        # 10. Sample notifications (so the bell icon has something to show in a demo)
        from apps.core.models import Notification, ContactMessage
        if not Notification.objects.filter(user=customer_user).exists():
            self.stdout.write("Creating sample notifications...")
            for o in Order.objects.filter(user=customer_user).order_by('created_at'):
                Notification.objects.create(
                    user=customer_user, notification_type='ORDER', link_url=f"/orders/{o.order_number}/tracking/",
                    title=f"#{o.order_number}: {o.get_status_display()}",
                    message="Track your order live with the animated rider map.",
                )
            Notification.objects.create(
                user=customer_user, notification_type='RESCUE', link_url='/smart/expiry-deals/',
                title="Fresh rescue deals near you",
                message="Dairy & bakery items are up to 60% off today. Save money and stop food waste!",
            )
            Notification.objects.create(
                user=customer_user, notification_type='SYSTEM', link_url='/smart/scanner/',
                title="Welcome to SmartKart AI 🎉",
                message="Snap your handwritten grocery list with the AI List Scanner to fill your cart in seconds.",
            )
        if not Notification.objects.filter(user=delivery_user).exists():
            for o in Order.objects.filter(delivery_partner=delivery_user).exclude(status__in=['DELIVERED', 'CANCELLED']):
                Notification.objects.create(
                    user=delivery_user, notification_type='ORDER', link_url=f"/delivery/order/{o.order_number}/",
                    title=f"New delivery: #{o.order_number}",
                    message=f"Deliver to {o.shipping_full_name}, {o.shipping_city} - {o.shipping_postal_code}.",
                )
        if not ContactMessage.objects.exists():
            ContactMessage.objects.create(
                name='Rohit Mehta', email='rohit@example.com', phone='9811122233',
                subject='Request: add Frozen Foods category',
                message='Love the 15-minute delivery! Could you please add frozen peas and ice creams?',
            )

        if refresh_dates:
            self.stdout.write(self.style.NOTICE("Demo expiry dates re-based on today's date."))
        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] SmartKart AI database seeding completed successfully!"))
        self.stdout.write(self.style.SUCCESS("Demo credentials: 'customer' / 'password123', 'admin' / 'password123', 'delivery' / 'password123'"))

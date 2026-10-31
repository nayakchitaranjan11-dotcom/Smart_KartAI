from django import template

register = template.Library()


@register.filter(name='make_list_split')
def make_list_split(value, delimiter=','):
    if value:
        return [item.strip() for item in value.split(delimiter) if item.strip()]
    return []


@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Product visuals (added)
# The catalogue ships without photos, so every product card shows a matching
# emoji on a soft category-coloured tile instead of the same grey bag icon.
# A real uploaded product.image is always shown first when it exists.
# ---------------------------------------------------------------------------

# (keywords, emoji) - checked in order, first keyword found in the product name wins
PRODUCT_EMOJI_RULES = [
    (('strawberr',), '🍓'), (('banana',), '🍌'), (('apple',), '🍎'), (('mango',), '🥭'), (('orange juice', 'orange'), '🍊'),
    (('grape',), '🍇'), (('lemon', 'citrus'), '🍋'), (('coconut',), '🥥'), (('tomato ketchup', 'ketchup'), '🥫'),
    (('tomato',), '🍅'), (('potato', 'aloo'), '🥔'), (('onion', 'pyaz'), '🧅'), (('garlic', 'lehsun'), '🧄'),
    (('ginger', 'adrak'), '🫚'), (('chilli', 'chili', 'mirch'), '🌶️'), (('coriander', 'dhaniya', 'spinach', 'palak', 'leaf'), '🌿'),
    (('carrot',), '🥕'), (('cucumber',), '🥒'), (('broccoli',), '🥦'), (('corn',), '🌽'), (('mushroom',), '🍄'),
    (('milk',), '🥛'), (('paneer', 'cheese'), '🧀'), (('butter',), '🧈'), (('ghee',), '🫙'), (('yogurt', 'dahi', 'curd'), '🥣'),
    (('egg',), '🥚'), (('bread',), '🍞'), (('cookie', 'biscuit'), '🍪'), (('chocolate',), '🍫'),
    (('chips', 'crisps'), '🍟'), (('bhujia', 'namkeen', 'sev'), '🥨'), (('almond', 'badam', 'cashew', 'nut'), '🥜'),
    (('tea', 'chai'), '🍵'), (('coffee',), '☕'), (('cola', 'soda', 'can'), '🥤'), (('juice',), '🧃'), (('water',), '💧'),
    (('noodle', 'maggi'), '🍜'), (('pasta', 'penne', 'spaghetti'), '🍝'), (('mayonnaise', 'mayo', 'sauce'), '🫙'),
    (('rice', 'poha'), '🍚'), (('atta', 'flour', 'wheat'), '🌾'), (('dal', 'chana', 'chickpea', 'rajma', 'lentil'), '🫘'),
    (('sugar',), '🍬'), (('salt',), '🧂'), (('turmeric', 'haldi', 'cumin', 'jeera', 'mustard', 'rai', 'masala', 'spice'), '🌰'),
    (('oil',), '🫗'), (('honey',), '🍯'), (('jam',), '🍓'),
    (('toothpaste', 'toothbrush'), '🪥'), (('handwash', 'soap', 'sanitizer'), '🧼'), (('shampoo', 'lotion', 'cream'), '🧴'),
    (('detergent', 'surf', 'laundry'), '🧺'), (('floor', 'cleaner', 'lizol', 'phenyl'), '🧽'), (('dishwash', 'vim'), '🍽️'),
    (('ice cream',), '🍨'), (('frozen', 'peas'), '🧊'), (('chicken',), '🍗'), (('fish',), '🐟'),
]

CATEGORY_STYLE_RULES = [
    # (keyword in category name, fallback emoji, tile colour)
    ('fruit', '🥬', '#EAF7E5'), ('vegetable', '🥬', '#EAF7E5'),
    ('dairy', '🥛', '#EAF3FF'), ('breakfast', '🥛', '#EAF3FF'),
    ('staple', '🌾', '#FFF6E0'), ('grain', '🌾', '#FFF6E0'),
    ('snack', '🍪', '#FFEFE3'), ('munch', '🍪', '#FFEFE3'),
    ('drink', '🥤', '#E6F7FA'), ('juice', '🥤', '#E6F7FA'),
    ('instant', '🍜', '#FFF1E8'), ('packaged', '🍜', '#FFF1E8'),
    ('household', '🧽', '#F1EEFF'), ('personal', '🧴', '#FCEBF4'),
    ('frozen', '🧊', '#E8F1FB'),
]

DEFAULT_TILE = ('🛒', '#F1F5F9')


def _category_style(product):
    name = getattr(getattr(product, 'category', None), 'name', '') or ''
    name = name.lower()
    for keyword, emoji, colour in CATEGORY_STYLE_RULES:
        if keyword in name:
            return emoji, colour
    return DEFAULT_TILE


def emoji_for_product(product):
    """Pure-python helper (also used by the search-suggestion API and the Tkinter app)."""
    if product is None:
        return DEFAULT_TILE[0]
    name = (getattr(product, 'name', '') or '').lower()
    for keywords, emoji in PRODUCT_EMOJI_RULES:
        if any(k in name for k in keywords):
            return emoji
    return _category_style(product)[0]


@register.filter(name='product_emoji')
def product_emoji(product):
    return emoji_for_product(product)


@register.filter(name='product_tile_color')
def product_tile_color(product):
    return _category_style(product)[1]


RECIPE_EMOJI_RULES = [
    (('chai', 'tea'), '☕'), (('pasta', 'penne'), '🍝'), (('sandwich',), '🥪'), (('poha',), '🍚'),
    (('pulao', 'biryani', 'rice'), '🍛'), (('dal',), '🍲'), (('chole', 'chana', 'rajma'), '🫘'),
    (('paneer',), '🧀'), (('salad',), '🥗'), (('soup',), '🍜'), (('cake', 'dessert', 'halwa', 'kheer'), '🍮'),
    (('egg', 'omelette'), '🍳'), (('pizza',), '🍕'), (('burger',), '🍔'), (('paratha', 'roti'), '🫓'),
]


@register.filter(name='recipe_emoji')
def recipe_emoji(recipe):
    name = (getattr(recipe, 'name', '') or '').lower()
    for keywords, emoji in RECIPE_EMOJI_RULES:
        if any(k in name for k in keywords):
            return emoji
    return '🍽️'

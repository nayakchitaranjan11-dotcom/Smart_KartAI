"""
Unit Conversion Helper (used by Recipe-to-Cart)
-----------------------------------------------
Converts recipe ingredient amounts (e.g. "250 g", "2 tbsp", "300 ml") and
catalogue pack sizes (e.g. "1 kg", "500 ml", "1 L") into a common base unit
so we can work out HOW MANY PACKS of a product a recipe really needs.

Base units:
    weight -> grams (g)
    volume -> millilitres (ml)
    count  -> pieces (pcs)

Example:
    Recipe needs 1.5 kg tomatoes for 8 people, catalogue sells "1 kg" packs
    -> packs_needed = ceil(1500 g / 1000 g) = 2 packs
"""

import math
import re
from decimal import Decimal

# factor to convert the given unit into its base unit, and which dimension it belongs to
UNIT_TABLE = {
    # weight (base = g)
    'g': (1, 'weight'), 'gm': (1, 'weight'), 'gms': (1, 'weight'), 'gram': (1, 'weight'), 'grams': (1, 'weight'),
    'kg': (1000, 'weight'), 'kgs': (1000, 'weight'), 'kilo': (1000, 'weight'), 'kilogram': (1000, 'weight'),
    # volume (base = ml)
    'ml': (1, 'volume'), 'l': (1000, 'volume'), 'lt': (1000, 'volume'), 'ltr': (1000, 'volume'),
    'litre': (1000, 'volume'), 'liter': (1000, 'volume'), 'litres': (1000, 'volume'),
    # kitchen spoons are treated as ~ grams/ml (good enough for shopping estimation)
    'tbsp': (15, 'spoon'), 'tsp': (5, 'spoon'),
    # countable
    'piece': (1, 'count'), 'pieces': (1, 'count'), 'pc': (1, 'count'), 'pcs': (1, 'count'),
    'dozen': (12, 'count'), 'doz': (12, 'count'),
}

PACK_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)')


def to_base(quantity, unit):
    """Return (amount_in_base_unit, dimension) or (None, None) if the unit is unknown."""
    if quantity is None or not unit:
        return None, None
    info = UNIT_TABLE.get(str(unit).strip().lower())
    if not info:
        return None, None
    factor, dimension = info
    return float(quantity) * factor, dimension


def parse_pack_size(unit_string):
    """
    Parse a catalogue pack label like "500 g", "1 kg", "1 L", "6 pcs" or "2 x 200 ml".
    Returns (amount_in_base_unit, dimension) or (None, None).
    """
    if not unit_string:
        return None, None
    text = str(unit_string).lower().replace(',', '')
    multi = re.match(r'\s*(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*([a-z]+)', text)
    if multi:
        count, qty, unit = multi.groups()
        amount, dim = to_base(float(qty), unit)
        return (amount * int(count), dim) if amount else (None, None)
    match = PACK_PATTERN.search(text)
    if not match:
        return None, None
    return to_base(match.group(1), match.group(2))


def _compatible(dim_a, dim_b):
    """Spoon measures can be compared with both weight and volume packs."""
    if dim_a == dim_b:
        return True
    return 'spoon' in (dim_a, dim_b) and ({dim_a, dim_b} - {'spoon'}) <= {'weight', 'volume'}


def packs_needed(required_qty, required_unit, product):
    """
    How many catalogue packs of `product` are required to cover `required_qty required_unit`.
    Falls back to 1 pack when the units cannot be compared (e.g. "4 piece" bread vs "400 g" loaf).
    """
    if product is None:
        return 0
    need, need_dim = to_base(required_qty, required_unit)
    pack, pack_dim = parse_pack_size(product.unit)
    if not need or not pack or not _compatible(need_dim, pack_dim):
        return 1
    return max(1, math.ceil(round(need / pack, 4)))


def format_qty(value):
    """Pretty print a Decimal/float without trailing zeros: 250.00 -> 250, 0.50 -> 0.5"""
    if value is None:
        return ''
    d = Decimal(str(value)).normalize()
    return format(d, 'f')

"""
AI Grocery List Scanner Engine
------------------------------
Extracts and parses written or typed grocery lists from images, pre-processes
the images with Pillow, extracts lines via pytesseract OCR (or graceful manual fallback),
extracts quantities/units using regex, and fuzzy-matches items against the product catalogue.
"""

import re
import difflib
from decimal import Decimal
from PIL import Image, ImageEnhance, ImageFilter
from django.conf import settings
from apps.catalogue.models import Product
from apps.smart_features.substitution_engine import SubstitutionEngine

try:
    import pytesseract
    if getattr(settings, 'TESSERACT_CMD', ''):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


class OCRGroceryScanner:
    @staticmethod
    def preprocess_image(image_file_or_path):
        """
        Preprocesses an image with Pillow: converts to grayscale, enhances contrast,
        and applies gentle sharpening for enhanced character recognition.
        """
        try:
            img = Image.open(image_file_or_path)
            # Convert to grayscale
            gray_img = img.convert('L')
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray_img)
            contrast_img = enhancer.enhance(2.0)
            # Gentle sharp filter
            sharp_img = contrast_img.filter(ImageFilter.SHARPEN)
            return sharp_img
        except Exception:
            return None

    @classmethod
    def extract_text_from_image(cls, image_path):
        """
        Extracts raw text from image using pytesseract if available.
        Returns (text, is_ocr_success).
        """
        if not TESSERACT_AVAILABLE:
            return "", False

        preprocessed = cls.preprocess_image(image_path)
        if not preprocessed:
            return "", False

        try:
            raw_text = pytesseract.image_to_string(preprocessed)
            if raw_text and len(raw_text.strip()) > 0:
                return raw_text.strip(), True
            return "", False
        except Exception:
            # Fallback if tesseract binary is not installed on system
            return "", False

    @staticmethod
    def parse_line_quantity(line):
        """
        Parses a single grocery line to separate item name, quantity, and unit.
        Examples:
          "Milk 2 packets" -> name: "Milk", qty: 2, unit: "packets"
          "Basmati Rice 5 kg" -> name: "Basmati Rice", qty: 5, unit: "kg"
          "Tomatoes 500g" -> name: "Tomatoes", qty: 0.5 or 500, unit: "g"
          "Eggs 1 dozen" -> name: "Eggs", qty: 1, unit: "dozen"
          "Sugar 1kg" -> name: "Sugar", qty: 1, unit: "kg"
          "Butter" -> name: "Butter", qty: 1, unit: "pack"
        """
        clean_line = re.sub(r'^[0-9\-\*\•\.\)]+\s*', '', line.strip()) # remove leading bullet/numbers
        clean_line = clean_line.strip()
        if not clean_line:
            return "", Decimal('1.00'), "unit"

        # Regex patterns for common quantities and units
        patterns = [
            # e.g., "Rice 5 kg" or "Rice 5.5 kg"
            r'^(.*?)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|kilo|kilogram|g|gm|gms|gram|grams|l|lt|liter|litres|litre|ml|packet|packets|pkt|pkts|pack|packs|bottle|bottles|box|boxes|can|cans|piece|pieces|pcs|pc|dozen|doz)\b(.*)$',
            # e.g., "5 kg Rice" or "2 packets Milk"
            r'^(\d+(?:\.\d+)?)\s*(kg|kgs|kilo|kilogram|g|gm|gms|gram|grams|l|lt|liter|litres|litre|ml|packet|packets|pkt|pkts|pack|packs|bottle|bottles|box|boxes|can|cans|piece|pieces|pcs|pc|dozen|doz)\s+(.*)$',
            # e.g., "Rice - 2"
            r'^(.*?)\s*[-:]\s*(\d+(?:\.\d+)?)\s*(.*)$',
        ]

        # Try pattern 1
        m1 = re.match(patterns[0], clean_line, re.IGNORECASE)
        if m1:
            name = (m1.group(1) + " " + m1.group(4)).strip()
            qty = Decimal(m1.group(2))
            unit = m1.group(3).lower()
            return name, qty, unit

        # Try pattern 2
        m2 = re.match(patterns[1], clean_line, re.IGNORECASE)
        if m2:
            qty = Decimal(m2.group(1))
            unit = m2.group(2).lower()
            name = m2.group(3).strip()
            return name, qty, unit

        # Try pattern 3
        m3 = re.match(patterns[2], clean_line, re.IGNORECASE)
        if m3:
            name = m3.group(1).strip()
            qty = Decimal(m3.group(2))
            unit = m3.group(3).strip().lower() or "pack"
            return name, qty, unit

        # Fallback default
        return clean_line, Decimal('1.00'), "pack"

    @classmethod
    def match_item_to_product(cls, item_name, all_products=None):
        """
        Fuzzy matches item name against product catalogue with token-based scoring.
        Returns (best_product, confidence_percent, alternative_suggestions).
        """
        if all_products is None:
            all_products = list(Product.objects.filter(is_active=True).select_related('category', 'brand'))

        clean_query = item_name.strip().lower()
        if not clean_query:
            return None, 0.0, []

        query_tokens = set(re.findall(r'\w+', clean_query))

        best_product = None
        best_score = 0.0

        for prod in all_products:
            prod_name = prod.name.lower()
            prod_cat = prod.category.name.lower()
            prod_tokens = set(re.findall(r'\w+', prod_name))
            
            # Sequence matcher ratio
            seq_ratio = difflib.SequenceMatcher(None, clean_query, prod_name).ratio()
            
            # Token containment score
            token_overlap = query_tokens.intersection(prod_tokens)
            token_score = (len(token_overlap) / max(len(query_tokens), 1))

            # If query is direct substring of product name or vice versa
            substring_bonus = 0.2 if (clean_query in prod_name or prod_name in clean_query) else 0.0

            # Category keyword boost
            cat_bonus = 0.15 if any(t in prod_cat for t in query_tokens) else 0.0

            # Total calculated score
            combined_score = (seq_ratio * 0.45) + (token_score * 0.40) + substring_bonus + cat_bonus
            combined_score = min(combined_score * 100.0, 100.0)

            if combined_score > best_score:
                best_score = combined_score
                best_product = prod

        alternatives = []
        if best_product and not best_product.is_in_stock:
            alternatives = SubstitutionEngine.get_substitutes(best_product, limit=2)
        elif best_score < 40.0:
            # Low confidence - search by category or general search
            alternatives = SubstitutionEngine.get_substitutes(best_product, limit=2) if best_product else []

        return best_product, round(best_score, 1), alternatives

    @classmethod
    def parse_full_list(cls, text_content):
        """
        Parses multi-line text string into structured matched items.
        """
        lines = [l.strip() for l in text_content.split('\n') if l.strip()]
        all_products = list(Product.objects.filter(is_active=True).select_related('category', 'brand'))

        results = []
        for line in lines:
            item_name, qty, unit = cls.parse_line_quantity(line)
            matched_prod, confidence, alts = cls.match_item_to_product(item_name, all_products)
            
            is_confident = confidence >= 50.0
            results.append({
                'raw_line': line,
                'parsed_name': item_name,
                'quantity': qty,
                'unit': unit,
                'product': matched_prod,
                'confidence': confidence,
                'is_confident': is_confident,
                'in_stock': matched_prod.is_in_stock if matched_prod else False,
                'alternatives': alts,
                'approved': is_confident and (matched_prod.is_in_stock if matched_prod else False)
            })

        return results

"""
Smart Product Substitution Engine
---------------------------------
Explainable multi-factor scoring algorithm for recommending optimal, in-stock alternatives
when a grocery item is out of stock or unavailable.

Scoring Criteria Breakdown (Total 100 points):
1. Category Match (35 pts): Must belong to the exact same or related grocery category.
2. Nutritional Tags / Subcategory Overlap (20 pts): Matches attributes like 'Organic', 'Whole Wheat', 'Full Cream', etc.
3. Pack / Unit Size Compatibility (15 pts): Proximity in quantity/weight (e.g., 500g vs 500g or 1kg).
4. Brand Match / Reputable Brand (10 pts): Same trusted brand or high-repute equivalent.
5. Price Proximity (10 pts): Replacement cost is reasonably close (avoids recommending unexpectedly expensive items).
6. Customer Rating (10 pts): High customer rating (4.0+ stars) weighted appropriately.

Filter constraints:
- Must have stock > 0.
- Must not be expired (expiry_date >= today).
- Excludes the original product itself.
"""

from decimal import Decimal
from django.utils import timezone
from apps.catalogue.models import Product
import difflib


class SubstitutionEngine:
    @staticmethod
    def get_substitutes(target_product, limit=4):
        """
        Given an unavailable or selected product, finds and scores the best in-stock substitutes.
        Returns a list of dicts with 'product', 'score', 'price_diff', 'pack_diff', 'reasons'.
        """
        today = timezone.now().date()
        
        # Candidates: In-stock, not expired, active, excluding target
        candidates = Product.objects.filter(
            is_active=True,
            stock_quantity__gt=0
        ).exclude(pk=target_product.pk)

        # Filter out products whose expiry date is in the past
        valid_candidates = []
        for cand in candidates:
            if cand.expiry_date and cand.expiry_date < today:
                continue
            valid_candidates.append(cand)

        scored_candidates = []
        target_tags = set(target_product.tags_list)

        for cand in valid_candidates:
            score = 0.0
            reasons = []

            # 1. Category Match (35 points)
            if cand.category == target_product.category:
                score += 35.0
                reasons.append(f"Same category ({cand.category.name})")
            else:
                # Text similarity of category names
                cat_ratio = difflib.SequenceMatcher(None, cand.category.name.lower(), target_product.category.name.lower()).ratio()
                cat_pts = cat_ratio * 20.0
                score += cat_pts
                if cat_ratio > 0.6:
                    reasons.append("Related category item")

            # 2. Nutritional Tags / Keyword Match (20 points)
            cand_tags = set(cand.tags_list)
            if target_tags and cand_tags:
                overlap = target_tags.intersection(cand_tags)
                if overlap:
                    tag_score = (len(overlap) / max(len(target_tags), 1)) * 20.0
                    score += min(tag_score, 20.0)
                    reasons.append(f"Shares qualities: {', '.join(list(overlap)[:2])}")
            else:
                # Fallback to name word overlap
                target_words = set(target_product.name.lower().split())
                cand_words = set(cand.name.lower().split())
                common_words = target_words.intersection(cand_words)
                if common_words:
                    score += min(len(common_words) * 5.0, 15.0)
                    reasons.append(f"Similar product name match")

            # 3. Pack / Unit Size Match (15 points)
            if cand.unit.strip().lower() == target_product.unit.strip().lower():
                score += 15.0
                reasons.append(f"Identical pack size ({cand.unit})")
            elif cand.unit_type == target_product.unit_type and target_product.unit_value > 0:
                ratio = float(cand.unit_value / target_product.unit_value)
                if 0.8 <= ratio <= 1.25:
                    score += 12.0
                    reasons.append(f"Very close pack size ({cand.unit})")
                elif 0.5 <= ratio <= 2.0:
                    score += 7.0
                    reasons.append(f"Comparable size ({cand.unit})")

            # 4. Brand Match (10 points)
            if target_product.brand and cand.brand and target_product.brand == cand.brand:
                score += 10.0
                reasons.append(f"Same trusted brand ({cand.brand.name})")
            elif cand.brand:
                score += 4.0

            # 5. Price Proximity (10 points)
            target_price = float(target_product.selling_price)
            cand_price = float(cand.selling_price)
            if target_price > 0:
                price_ratio = min(target_price, cand_price) / max(target_price, cand_price)
                price_score = price_ratio * 10.0
                score += price_score
                if cand_price < target_price:
                    savings = target_price - cand_price
                    reasons.append(f"Saves ₹{savings:.2f}")
                elif price_ratio > 0.85:
                    reasons.append("Similar price point")

            # 6. Customer Rating (10 points)
            rating = float(cand.average_rating)
            rating_score = (rating / 5.0) * 10.0
            score += rating_score
            if rating >= 4.2:
                reasons.append(f"High customer rating ({rating:.1f}★)")

            # In-stock bonus guarantee
            if cand.stock_quantity >= 10:
                reasons.append("In stock & ready to ship")

            price_diff = cand.selling_price - target_product.selling_price
            
            scored_candidates.append({
                'product': cand,
                'score': round(score, 1),
                'price_diff': price_diff,
                'is_cheaper': price_diff < 0,
                'price_diff_abs': abs(price_diff),
                'primary_reason': reasons[0] if reasons else "Best matched in-stock grocery item",
                'all_reasons': reasons[:3],
            })

        # Sort by highest score first
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        return scored_candidates[:limit]

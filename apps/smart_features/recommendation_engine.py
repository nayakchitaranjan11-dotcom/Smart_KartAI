"""
Recommendation Engine (added)
-----------------------------
Two small, explainable recommenders that make the store feel "smart" like Blinkit:

1. Frequently Bought Together  (market-basket analysis / association rules)
   For a product A we look at every past order that contained A and count how often
   each other product B appears in those same orders.

        support(A)          = number of orders containing A
        support(A and B)    = number of orders containing both A and B
        confidence(A -> B)  = support(A and B) / support(A)

   Products with the highest confidence are recommended. When there is not enough order
   history yet (cold start), we fall back to products that appear together in the same
   RECIPES, and finally to top-rated products from the same category.

2. Buy Again
   Products the customer ordered before, ranked by how many times they bought them.
"""

from collections import Counter

from django.db.models import Count, Max

from apps.catalogue.models import Product
from apps.orders.models import OrderItem
from apps.smart_features.models import RecipeIngredient


def _available(qs):
    return qs.filter(is_active=True, stock_quantity__gt=0)


class RecommendationEngine:
    @staticmethod
    def frequently_bought_together(product, limit=4):
        results = []
        seen = {product.pk}

        # --- 1. Association rules from real order history ---
        order_ids = list(
            OrderItem.objects.filter(product=product)
            .exclude(order__status='CANCELLED')
            .values_list('order_id', flat=True).distinct()
        )
        support_a = len(order_ids)
        if support_a:
            pair_counts = (
                OrderItem.objects.filter(order_id__in=order_ids, product__isnull=False)
                .exclude(product=product)
                .values('product')
                .annotate(together=Count('order', distinct=True))
                .order_by('-together')
            )
            ids = [row['product'] for row in pair_counts]
            products = {p.pk: p for p in _available(Product.objects.filter(pk__in=ids))}
            for row in pair_counts:
                cand = products.get(row['product'])
                if cand and cand.pk not in seen:
                    confidence = round(row['together'] / support_a * 100)
                    results.append({
                        'product': cand,
                        'confidence': confidence,
                        'reason': f"Bought together in {confidence}% of orders with this item",
                        'source': 'orders',
                    })
                    seen.add(cand.pk)
                if len(results) >= limit:
                    return results

        # --- 2. Cold start: ingredients that share a recipe with this product ---
        recipe_ids = RecipeIngredient.objects.filter(product=product).values_list('recipe_id', flat=True)
        if recipe_ids:
            co_ingredients = Counter(
                RecipeIngredient.objects.filter(recipe_id__in=list(recipe_ids), product__isnull=False)
                .exclude(product=product)
                .values_list('product_id', flat=True)
            )
            products = {p.pk: p for p in _available(Product.objects.filter(pk__in=list(co_ingredients)))}
            for pid, shared in co_ingredients.most_common():
                cand = products.get(pid)
                if cand and cand.pk not in seen:
                    results.append({
                        'product': cand,
                        'confidence': None,
                        'reason': f"Used together in {shared} recipe{'s' if shared > 1 else ''}",
                        'source': 'recipes',
                    })
                    seen.add(cand.pk)
                if len(results) >= limit:
                    return results

        # --- 3. Fallback: best rated items from the same aisle ---
        for cand in _available(Product.objects.filter(category=product.category)).exclude(pk__in=seen) \
                .order_by('-average_rating', '-total_reviews')[: max(0, limit - len(results))]:
            results.append({
                'product': cand,
                'confidence': None,
                'reason': f"Popular in {cand.category.name}",
                'source': 'category',
            })
        return results

    @staticmethod
    def buy_again(user, limit=8):
        """Products this customer bought before (most frequently bought first)."""
        if not user or not user.is_authenticated:
            return []
        rows = (
            OrderItem.objects.filter(order__user=user, product__isnull=False)
            .exclude(order__status='CANCELLED')
            .values('product')
            .annotate(times=Count('order', distinct=True), last_bought=Max('order__created_at'))
            .order_by('-times', '-last_bought', 'product')
        )
        ids = [r['product'] for r in rows]
        products = {p.pk: p for p in Product.objects.filter(pk__in=ids, is_active=True).select_related('category')}
        ordered = []
        for r in rows:
            p = products.get(r['product'])
            if p:
                p.times_bought = r['times']
                ordered.append(p)
            if len(ordered) >= limit:
                break
        return ordered

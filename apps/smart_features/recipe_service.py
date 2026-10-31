"""
Recipe-to-Cart Service
----------------------
Calculates dynamic ingredient requirements scaled to any number of servings,
maps ingredients to live product catalogue stock, suggests substitutions for unavailable ingredients,
and handles batch additions to cart with pantry exclusions.
"""

from decimal import Decimal
from apps.smart_features.substitution_engine import SubstitutionEngine
from apps.smart_features.units import packs_needed
from apps.cart.models import CartItem


class RecipeService:
    @staticmethod
    def get_recipe_ingredients_data(recipe, target_servings=4):
        """
        Returns structured ingredient data scaled to target servings.
        """
        base_servings = recipe.base_servings or 4
        ratio = Decimal(str(target_servings)) / Decimal(str(base_servings))

        ingredients_data = []
        total_estimated_cost = Decimal('0.00')
        all_in_stock = True

        for ing in recipe.ingredients.all():
            scaled_qty = (ing.quantity_per_base_servings * ratio).quantize(Decimal('0.01'))
            prod = ing.product
            in_stock = prod.is_in_stock if prod else False
            
            substitutes = []
            if prod and not in_stock:
                all_in_stock = False
                substitutes = SubstitutionEngine.get_substitutes(prod, limit=2)
            elif not prod:
                all_in_stock = False

            # How many catalogue packs cover the scaled quantity (e.g. 1.2 kg needed, 1 kg pack -> 2 packs)
            packs = packs_needed(scaled_qty, ing.unit, prod) if prod else 0
            line_cost = (prod.selling_price * packs) if prod else Decimal('0.00')
            if prod:
                total_estimated_cost += line_cost

            ingredients_data.append({
                'ingredient': ing,
                'name': ing.ingredient_name,
                'scaled_quantity': scaled_qty,
                'unit': ing.unit,
                'is_optional': ing.is_optional,
                'notes': ing.notes,
                'product': prod,
                'in_stock': in_stock,
                'price': prod.selling_price if prod else None,
                'packs_needed': packs,
                'line_cost': line_cost,
                'substitutes': substitutes,
            })

        return {
            'recipe': recipe,
            'target_servings': target_servings,
            'base_servings': base_servings,
            'ingredients': ingredients_data,
            'total_estimated_cost': total_estimated_cost,
            'all_in_stock': all_in_stock,
        }

    @staticmethod
    def add_recipe_to_cart(cart, recipe, selected_ingredient_ids, target_servings=4):
        """
        Adds selected available recipe ingredients to cart, scaling quantities accordingly.
        Returns (added_count, skipped_count, message).
        """
        ingredients_info = RecipeService.get_recipe_ingredients_data(recipe, target_servings)
        added_count = 0
        skipped_count = 0

        for item in ingredients_info['ingredients']:
            ing_id = str(item['ingredient'].id)
            if ing_id in selected_ingredient_ids:
                prod = item['product']
                if prod and prod.is_in_stock:
                    # Units needed now follow the selected servings (minimum 1 pack, capped by stock)
                    qty_to_add = min(max(1, item['packs_needed']), prod.stock_quantity)
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=prod,
                        defaults={'quantity': qty_to_add}
                    )
                    if not created:
                        # Keep whichever is larger: what's already in the cart or what the recipe needs
                        new_qty = min(max(cart_item.quantity, qty_to_add), prod.stock_quantity)
                        cart_item.quantity = new_qty
                        cart_item.save()
                    added_count += 1
                else:
                    skipped_count += 1

        return added_count, skipped_count

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json

from apps.catalogue.models import Product, Category
from apps.cart.models import CartItem
from apps.cart.utils import get_or_create_cart
from apps.smart_features.models import (
    MonthlyBudget, Recipe, RecipeIngredient,
    GroceryScan, GroceryScanItem, ExpiryRescueDeal
)
from apps.smart_features.substitution_engine import SubstitutionEngine
from apps.smart_features.ocr_scanner import OCRGroceryScanner, TESSERACT_AVAILABLE
from apps.smart_features.budget_service import BudgetService
from apps.smart_features.recipe_service import RecipeService
from apps.smart_features.expiry_service import ExpiryRescueService


# ==========================================
# 1. AI GROCERY LIST SCANNER
# ==========================================

def scanner_view(request):
    """
    Renders upload form for grocery list image or direct text entry fallback.
    """
    if request.method == 'POST':
        image_file = request.FILES.get('grocery_image')
        manual_text = request.POST.get('manual_text', '').strip()

        extracted_text = ""
        ocr_success = False

        if image_file:
            # Validate extension
            valid_exts = ['jpg', 'jpeg', 'png', 'webp']
            ext = image_file.name.split('.')[-1].lower()
            if ext not in valid_exts:
                messages.error(request, "Invalid file format. Please upload a JPG, JPEG, or PNG image.")
                return redirect('smart_features:scanner')

            # Save scan record
            scan = GroceryScan.objects.create(
                user=request.user if request.user.is_authenticated else None,
                image=image_file
            )

            # Perform OCR if available
            extracted_text, ocr_success = OCRGroceryScanner.extract_text_from_image(scan.image.path)
            scan.raw_extracted_text = extracted_text
            scan.is_ocr_available = ocr_success
            scan.save()

            if not ocr_success:
                messages.info(request, "Tesseract OCR engine is processing in manual assistance mode. You can edit the text below to match items.")

        elif manual_text:
            extracted_text = manual_text
            ocr_success = True

        if extracted_text:
            parsed_items = OCRGroceryScanner.parse_full_list(extracted_text)
            return render(request, 'smart_features/scanner_results.html', {
                'extracted_text': extracted_text,
                'parsed_items': parsed_items,
                'ocr_available': TESSERACT_AVAILABLE,
                'ocr_success': ocr_success,
            })
        else:
            messages.warning(request, "Could not extract text. Please enter your grocery list manually below.")

    return render(request, 'smart_features/scanner.html', {
        'ocr_available': TESSERACT_AVAILABLE
    })


@require_POST
def scanner_add_to_cart_view(request):
    """
    Adds approved items from OCR / list scanner into cart.
    """
    cart = get_or_create_cart(request)
    product_ids = request.POST.getlist('product_id')
    quantities = request.POST.getlist('quantity')

    added_count = 0
    for prod_id, qty_str in zip(product_ids, quantities):
        if not prod_id:
            continue
        try:
            prod = Product.objects.get(pk=prod_id, is_active=True)
            qty = max(1, int(float(qty_str or 1)))
            if prod.is_in_stock:
                qty = min(qty, prod.stock_quantity)
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=prod,
                    defaults={'quantity': qty}
                )
                if not created:
                    cart_item.quantity = min(cart_item.quantity + qty, prod.stock_quantity)
                    cart_item.save()
                added_count += 1
        except Exception:
            continue

    if added_count > 0:
        messages.success(request, f"Successfully added {added_count} items from your grocery list to cart!")
    else:
        messages.warning(request, "No items were selected or available to add.")

    return redirect('cart:cart_detail')


# ==========================================
# 2. MONTHLY BUDGET SMART CART
# ==========================================

@login_required
def budget_dashboard_view(request):
    cart = get_or_create_cart(request)
    budget_data = BudgetService.get_budget_dashboard_data(request.user, cart=cart)

    return render(request, 'smart_features/budget_dashboard.html', {
        'budget_data': budget_data,
        'cart': cart,
    })


@login_required
@require_POST
def update_budget_settings_view(request):
    try:
        new_budget = Decimal(request.POST.get('budget_amount', '5000'))
        threshold = int(request.POST.get('warning_threshold_percent', 80))

        if new_budget < Decimal('100.00'):
            messages.error(request, "Monthly budget must be at least ₹100.")
            return redirect('smart_features:budget_dashboard')

        # Update or create for this month
        now = timezone.now()
        budget_obj, _ = MonthlyBudget.objects.get_or_create(
            user=request.user,
            month=now.month,
            year=now.year,
            defaults={'budget_amount': new_budget, 'warning_threshold_percent': threshold}
        )
        budget_obj.budget_amount = new_budget
        budget_obj.warning_threshold_percent = threshold
        budget_obj.save()

        # Update customer profile default
        if hasattr(request.user, 'customer_profile'):
            profile = request.user.customer_profile
            profile.monthly_budget = new_budget
            profile.budget_warning_threshold = threshold
            profile.save()

        messages.success(request, f"Monthly budget updated to ₹{new_budget} (Alert at {threshold}%).")
    except Exception as e:
        messages.error(request, f"Error updating budget: {e}")

    return redirect('smart_features:budget_dashboard')


@login_required
@require_POST
def swap_cheaper_item_view(request):
    """
    1-Click swap a cart item with a cheaper recommended alternative to save money.
    """
    cart_item_id = request.POST.get('cart_item_id')
    cheaper_prod_id = request.POST.get('cheaper_prod_id')

    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart=cart)
    cheaper_prod = get_object_or_404(Product, pk=cheaper_prod_id, is_active=True)

    if not cheaper_prod.is_in_stock:
        messages.error(request, f"'{cheaper_prod.name}' is currently out of stock.")
        return redirect('smart_features:budget_dashboard')

    old_name = cart_item.product.name
    qty = min(cart_item.quantity, cheaper_prod.stock_quantity)
    cart_item.delete()

    new_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=cheaper_prod,
        defaults={'quantity': qty}
    )
    if not created:
        new_item.quantity = min(new_item.quantity + qty, cheaper_prod.stock_quantity)
        new_item.save()

    messages.success(request, f"Smart Swap: Replaced '{old_name}' with '{cheaper_prod.name}'! You saved on your budget.")
    return redirect('smart_features:budget_dashboard')


# ==========================================
# 3. RECIPE-TO-CART
# ==========================================

def recipe_list_view(request):
    recipes = Recipe.objects.all().prefetch_related('ingredients', 'ingredients__product')

    diet = request.GET.get('diet')
    cuisine = request.GET.get('cuisine')
    difficulty = request.GET.get('difficulty')

    if diet:
        recipes = recipes.filter(diet_type=diet)
    if cuisine:
        recipes = recipes.filter(cuisine__iexact=cuisine)
    if difficulty:
        recipes = recipes.filter(difficulty=difficulty)

    return render(request, 'smart_features/recipe_list.html', {
        'recipes': recipes,
        'selected_diet': diet or '',
        'selected_cuisine': cuisine or '',
        'selected_difficulty': difficulty or '',
    })


def recipe_detail_view(request, slug):
    recipe = get_object_or_404(Recipe, slug=slug)
    servings = int(request.GET.get('servings', recipe.base_servings or 4))
    if servings not in [2, 4, 6, 8]:
        servings = recipe.base_servings or 4

    recipe_info = RecipeService.get_recipe_ingredients_data(recipe, target_servings=servings)

    return render(request, 'smart_features/recipe_detail.html', {
        'recipe': recipe,
        'recipe_info': recipe_info,
        'selected_servings': servings,
        'serving_options': [2, 4, 6, 8],
    })


@require_POST
def recipe_add_to_cart_view(request, slug):
    recipe = get_object_or_404(Recipe, slug=slug)
    servings = int(request.POST.get('servings', recipe.base_servings or 4))
    selected_ingredients = request.POST.getlist('ingredient_id')

    if not selected_ingredients:
        messages.warning(request, "Please select at least one ingredient to add to cart.")
        return redirect('smart_features:recipe_detail', slug=slug)

    cart = get_or_create_cart(request)
    added, skipped = RecipeService.add_recipe_to_cart(cart, recipe, selected_ingredients, target_servings=servings)

    if added > 0:
        messages.success(request, f"Added {added} ingredients for '{recipe.name}' to your cart!")
    if skipped > 0:
        messages.info(request, f"{skipped} ingredients were skipped as they are currently out of stock.")

    return redirect('cart:cart_detail')


# ==========================================
# 4. EXPIRY RESCUE DEALS
# ==========================================

def expiry_deals_view(request):
    deals = ExpiryRescueService.get_active_deals()
    rescued_total = ExpiryRescueService.get_total_rescued_items_count()

    return render(request, 'smart_features/expiry_deals.html', {
        'deals': deals,
        'rescued_total': rescued_total,
    })


@require_POST
def expiry_deal_add_to_cart_view(request, deal_id):
    deal = get_object_or_404(ExpiryRescueDeal, pk=deal_id)

    if not deal.is_currently_active:
        messages.error(request, "This rescue deal has expired or is no longer available.")
        return redirect('smart_features:expiry_deals')

    product = deal.product
    if product.stock_quantity <= 0:
        messages.error(request, f"'{product.name}' is out of stock.")
        return redirect('smart_features:expiry_deals')

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity = min(cart_item.quantity + 1, product.stock_quantity)
        cart_item.save()

    messages.success(request, f"Rescued '{product.name}' at ₹{deal.rescue_price} ({deal.rescue_discount_percent}% OFF) added to cart!")
    return redirect('cart:cart_detail')


# ==========================================
# 5. SMART PRODUCT SUBSTITUTION
# ==========================================

def product_substitution_view(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=product_id)
    substitutes = SubstitutionEngine.get_substitutes(product, limit=6)

    return render(request, 'smart_features/substitution_detail.html', {
        'product': product,
        'substitutes': substitutes,
    })


@require_POST
def substitute_in_cart_view(request):
    """
    Substitutes an out of stock product in the cart with the chosen replacement.
    """
    old_product_id = request.POST.get('old_product_id')
    new_product_id = request.POST.get('new_product_id')

    cart = get_or_create_cart(request)
    old_item = CartItem.objects.filter(cart=cart, product_id=old_product_id).first()
    new_prod = get_object_or_404(Product, pk=new_product_id, is_active=True)

    if not new_prod.is_in_stock:
        messages.error(request, f"Substitute '{new_prod.name}' is also currently out of stock.")
        return redirect('smart_features:substitution_detail', product_id=old_product_id)

    qty = old_item.quantity if old_item else 1
    if old_item:
        old_item.delete()

    new_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=new_prod,
        defaults={'quantity': min(qty, new_prod.stock_quantity)}
    )
    if not created:
        new_item.quantity = min(new_item.quantity + qty, new_prod.stock_quantity)
        new_item.save()

    messages.success(request, f"Replaced with '{new_prod.name}' in your cart!")
    return redirect('cart:cart_detail')

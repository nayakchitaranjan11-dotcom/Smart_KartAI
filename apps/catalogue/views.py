from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Min, Max, F, ExpressionWrapper, FloatField, Value
from django.db.models.functions import Cast, NullIf
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal

from apps.catalogue.models import Category, Brand, Product, Review
from apps.orders.models import OrderItem
from apps.smart_features.substitution_engine import SubstitutionEngine
from apps.core.templatetags.core_tags import emoji_for_product
from apps.smart_features.recommendation_engine import RecommendationEngine


def product_list_view(request):
    """
    Main product catalogue view with faceted search, filtering, and sorting.
    """
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')

    # 1. Category Filter
    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=selected_category)

    # 2. Brand Filter
    brand_slug = request.GET.get('brand')
    selected_brand = None
    if brand_slug:
        selected_brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
        products = products.filter(brand=selected_brand)

    # 3. Price Filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(selling_price__gte=Decimal(min_price))
        except Exception:
            pass
    if max_price:
        try:
            products = products.filter(selling_price__lte=Decimal(max_price))
        except Exception:
            pass

    # 4. Stock filter
    in_stock_only = request.GET.get('in_stock')
    if in_stock_only == '1':
        products = products.filter(stock_quantity__gt=0)

    # 5. Nutritional Tag Filter
    tag = request.GET.get('tag')
    if tag:
        products = products.filter(nutritional_tags__icontains=tag)

    # 6. Sorting
    sort_by = request.GET.get('sort', 'popular')
    if sort_by == 'price_low':
        products = products.order_by('selling_price')
    elif sort_by == 'price_high':
        products = products.order_by('-selling_price')
    elif sort_by == 'discount':
        # discount_percent is a Python @property, so the DB cannot sort on it directly.
        # We annotate an equivalent SQL expression: (MRP - selling price) / MRP
        # (Cast to float so SQLite does not do integer division; NullIf avoids divide-by-zero.)
        products = products.annotate(
            discount_ratio=ExpressionWrapper(
                Cast(F('original_price') - F('selling_price'), FloatField())
                / NullIf(Cast(F('original_price'), FloatField()), Value(0.0)),
                output_field=FloatField()
            )
        ).order_by('-discount_ratio', '-selling_price')
    elif sort_by == 'rating':
        products = products.order_by('-average_rating', '-total_reviews')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else: # Default
        products = products.order_by('-is_featured', '-total_reviews', '-created_at')

    # Pagination: 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    brands = Brand.objects.filter(is_active=True).order_by('name')

    return render(request, 'catalogue/product_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'sort_by': sort_by,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'in_stock_only': in_stock_only == '1',
        'selected_tag': tag or '',
        'total_count': products.count(),
    })


def category_products_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(category=category, is_active=True).select_related('brand').order_by('-is_featured', '-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalogue/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
        'total_count': products.count(),
    })


def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), slug=slug, is_active=True)
    
    # Similar products in same category
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=product.pk).order_by('?')[:4]

    # If out of stock, fetch intelligent substitutes
    substitutes = []
    if not product.is_in_stock:
        substitutes = SubstitutionEngine.get_substitutes(product, limit=3)

    # Reviews and verified purchase check
    reviews = product.reviews.all().select_related('user').order_by('-created_at')
    can_review = False
    if request.user.is_authenticated:
        # Check if user bought this product in a DELIVERED order
        has_delivered_order = OrderItem.objects.filter(
            order__user=request.user,
            order__status='DELIVERED',
            product=product
        ).exists()
        already_reviewed = Review.objects.filter(product=product, user=request.user).exists()
        can_review = has_delivered_order and not already_reviewed

    return render(request, 'catalogue/product_detail.html', {
        'product': product,
        'similar_products': similar_products,
        'substitutes': substitutes,
        'reviews': reviews,
        'can_review': can_review,
        'bought_together': RecommendationEngine.frequently_bought_together(product, limit=4),
    })


def product_search_view(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.none()

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(nutritional_tags__icontains=query),
            is_active=True
        ).select_related('category', 'brand').distinct()

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalogue/search_results.html', {
        'query': query,
        'page_obj': page_obj,
        'total_count': products.count(),
    })


def search_suggestions_api(request):
    """
    JSON API for live autocomplete search suggestions.
    """
    query = request.GET.get('term', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(category__name__icontains=query),
        is_active=True
    ).select_related('category')[:6]

    results = []
    for p in products:
        results.append({
            'name': p.name,
            'unit': p.unit,
            'price': str(p.selling_price),
            'category': p.category.name,
            'url': f"/products/{p.slug}/",
            'image': p.image.url if p.image else '',
            'emoji': emoji_for_product(p),
        })

    return JsonResponse({'results': results})


@login_required
def add_review_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    if request.method == 'POST':
        # Verify customer purchase
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status='DELIVERED',
            product=product
        ).exists()

        if not has_purchased and not request.user.is_staff:
            messages.error(request, "You can only review products from delivered orders.")
            return redirect('catalogue:product_detail', slug=slug)

        if Review.objects.filter(product=product, user=request.user).exists():
            messages.warning(request, "You have already submitted a review for this product.")
            return redirect('catalogue:product_detail', slug=slug)

        rating = int(request.POST.get('rating', 5))
        headline = request.POST.get('headline', '').strip()
        comment = request.POST.get('comment', '').strip()

        if not (1 <= rating <= 5):
            rating = 5

        Review.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            headline=headline,
            comment=comment,
            is_verified_purchase=True
        )
        messages.success(request, "Thank you! Your verified review has been published.")

    return redirect('catalogue:product_detail', slug=slug)

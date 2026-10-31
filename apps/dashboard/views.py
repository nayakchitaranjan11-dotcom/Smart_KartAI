import csv
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from apps.accounts.decorators import admin_required
from apps.accounts.models import CustomerProfile, DeliveryProfile
from apps.catalogue.models import Product, Category, Brand, Review
from apps.orders.models import Order, OrderItem, OrderStatusHistory, DeliveryAssignment
from apps.cart.models import Coupon
from apps.smart_features.models import Recipe, RecipeIngredient, ExpiryRescueDeal
from apps.smart_features.expiry_service import ExpiryRescueService
from apps.core.models import ContactMessage


@admin_required
def admin_dashboard_view(request):
    today = timezone.now().date()
    now = timezone.now()

    # 1. KPI Counts
    total_users = User.objects.filter(is_staff=False).exclude(delivery_profile__isnull=False).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status__in=['PLACED', 'CONFIRMED', 'PACKING', 'ASSIGNED', 'PICKED_UP', 'OUT_FOR_DELIVERY']).count()
    delivered_orders = Order.objects.filter(status='DELIVERED').count()
    
    # Revenue
    revenue_res = Order.objects.exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))
    total_revenue = revenue_res['total'] or Decimal('0.00')

    today_sales_res = Order.objects.filter(created_at__date=today).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))
    today_sales = today_sales_res['total'] or Decimal('0.00')

    # Inventory alerts count
    low_stock_count = Product.objects.filter(is_active=True, stock_quantity__lte=10, stock_quantity__gt=0).count()
    out_of_stock_count = Product.objects.filter(is_active=True, stock_quantity=0).count()
    expiry_alerts = ExpiryRescueService.get_admin_expiry_alerts()
    near_expiry_count = len(expiry_alerts['critical']) + len(expiry_alerts['warning'])

    # Rescued items count
    rescued_total = ExpiryRescueService.get_total_rescued_items_count()

    # 2. Chart.js Data: Revenue over last 6 months
    month_labels = []
    month_revenue = []
    for i in range(5, -1, -1):
        # Step back whole calendar months (30-day steps repeated/skipped months, e.g. 'Oct' twice on 31 Oct)
        month_index = now.year * 12 + (now.month - 1) - i
        m_year, m_month = divmod(month_index, 12)
        m_month += 1
        m_name = datetime.date(m_year, m_month, 1).strftime('%b %Y')
        m_rev = Order.objects.filter(
            created_at__year=m_year,
            created_at__month=m_month
        ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')
        month_labels.append(m_name)
        month_revenue.append(float(m_rev))

    # 3. Chart.js Data: Order Status breakdown
    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}
    status_labels = ['Placed', 'Confirmed', 'Packing', 'Out for Delivery', 'Delivered', 'Cancelled']
    status_values = [
        status_dict.get('PLACED', 0),
        status_dict.get('CONFIRMED', 0),
        status_dict.get('PACKING', 0) + status_dict.get('READY_FOR_PICKUP', 0),
        status_dict.get('OUT_FOR_DELIVERY', 0) + status_dict.get('PICKED_UP', 0),
        status_dict.get('DELIVERED', 0),
        status_dict.get('CANCELLED', 0),
    ]

    # 4. Best-selling products
    best_sellers = OrderItem.objects.values(
        'product__name', 'product__category__name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_earned=Sum('total_price')
    ).order_by('-total_sold')[:5]

    # 5. Recent orders
    recent_orders = Order.objects.select_related('user', 'delivery_partner').order_by('-created_at')[:8]

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'today_sales': today_sales,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'near_expiry_count': near_expiry_count,
        'rescued_total': rescued_total,
        'month_labels': month_labels,
        'month_revenue': month_revenue,
        'status_labels': status_labels,
        'status_values': status_values,
        'best_sellers': best_sellers,
        'recent_orders': recent_orders,
        'open_messages_count': ContactMessage.objects.filter(is_resolved=False).count(),
    })


# ==========================================
# PRODUCT & CATALOGUE MANAGEMENT
# ==========================================

@admin_required
def admin_products_list(request):
    products = Product.objects.select_related('category', 'brand').order_by('-created_at')
    
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(category__name__icontains=q))

    cat_id = request.GET.get('category')
    if cat_id:
        products = products.filter(category_id=cat_id)

    paginator = Paginator(products, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    categories = Category.objects.all()

    return render(request, 'dashboard/products_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'selected_cat': cat_id or '',
    })


@admin_required
def admin_product_create(request):
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            category_id = request.POST.get('category')
            brand_id = request.POST.get('brand') or None
            description = request.POST.get('description', '')
            original_price = Decimal(request.POST.get('original_price', '0'))
            selling_price = Decimal(request.POST.get('selling_price', '0'))
            unit = request.POST.get('unit', '1 kg')
            unit_value = Decimal(request.POST.get('unit_value', '1.0'))
            unit_type = request.POST.get('unit_type', 'kg')
            stock_quantity = int(request.POST.get('stock_quantity', 50))
            reorder_level = int(request.POST.get('reorder_level', 10))
            expiry_date = request.POST.get('expiry_date') or None
            nutritional_tags = request.POST.get('nutritional_tags', '')
            is_featured = 'is_featured' in request.POST
            image = request.FILES.get('image')

            product = Product.objects.create(
                name=name,
                category_id=category_id,
                brand_id=brand_id,
                description=description,
                original_price=original_price,
                selling_price=selling_price,
                unit=unit,
                unit_value=unit_value,
                unit_type=unit_type,
                stock_quantity=stock_quantity,
                reorder_level=reorder_level,
                expiry_date=expiry_date,
                nutritional_tags=nutritional_tags,
                is_featured=is_featured,
                image=image
            )
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('dashboard:products_list')
        except Exception as e:
            messages.error(request, f"Error creating product: {e}")

    return render(request, 'dashboard/product_form.html', {
        'categories': categories,
        'brands': brands,
        'action': 'Add New Product'
    })


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.brand_id = request.POST.get('brand') or None
            product.description = request.POST.get('description', '')
            product.original_price = Decimal(request.POST.get('original_price', '0'))
            product.selling_price = Decimal(request.POST.get('selling_price', '0'))
            product.unit = request.POST.get('unit', '1 kg')
            product.unit_value = Decimal(request.POST.get('unit_value', '1.0'))
            product.unit_type = request.POST.get('unit_type', 'kg')
            product.stock_quantity = int(request.POST.get('stock_quantity', 50))
            product.reorder_level = int(request.POST.get('reorder_level', 10))
            product.expiry_date = request.POST.get('expiry_date') or None
            product.nutritional_tags = request.POST.get('nutritional_tags', '')
            product.is_featured = 'is_featured' in request.POST
            product.is_active = 'is_active' in request.POST

            if request.FILES.get('image'):
                product.image = request.FILES.get('image')

            product.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('dashboard:products_list')
        except Exception as e:
            messages.error(request, f"Error updating product: {e}")

    return render(request, 'dashboard/product_form.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'action': 'Edit Product'
    })


@admin_required
@require_POST
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.is_active = False # Safe soft-delete
    product.save()
    messages.info(request, f"Product '{name}' has been deactivated from catalogue.")
    return redirect('dashboard:products_list')


# ==========================================
# CATEGORY & BRAND MANAGEMENT
# ==========================================

@admin_required
def admin_categories_list(request):
    categories = Category.objects.annotate(prod_count=Count('products')).order_by('display_order', 'name')
    if request.method == 'POST':
        name = request.POST.get('name')
        icon_class = request.POST.get('icon_class', 'bi-basket')
        description = request.POST.get('description', '')
        if name:
            Category.objects.create(name=name, icon_class=icon_class, description=description)
            messages.success(request, f"Category '{name}' created!")
            return redirect('dashboard:categories_list')

    return render(request, 'dashboard/categories_list.html', {'categories': categories})


@admin_required
@require_POST
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    category.delete()
    messages.info(request, f"Category '{name}' deleted.")
    return redirect('dashboard:categories_list')


# ==========================================
# INVENTORY MANAGEMENT
# ==========================================

@admin_required
def admin_inventory_view(request):
    filter_type = request.GET.get('filter', 'all')
    products = Product.objects.filter(is_active=True).select_related('category')

    if filter_type == 'low':
        products = products.filter(stock_quantity__lte=10, stock_quantity__gt=0)
    elif filter_type == 'out':
        products = products.filter(stock_quantity=0)

    if request.method == 'POST':
        prod_id = request.POST.get('product_id')
        new_stock = int(request.POST.get('stock_quantity', 0))
        prod = get_object_or_404(Product, pk=prod_id)
        prod.stock_quantity = max(0, new_stock)
        prod.save(update_fields=['stock_quantity'])
        messages.success(request, f"Stock updated for '{prod.name}' to {prod.stock_quantity} units.")
        return redirect(f"/dashboard/inventory/?filter={filter_type}")

    return render(request, 'dashboard/inventory.html', {
        'products': products,
        'filter_type': filter_type,
    })


# ==========================================
# ORDER MANAGEMENT & DELIVERY ASSIGNMENT
# ==========================================

@admin_required
def admin_orders_list(request):
    orders = Order.objects.select_related('user', 'delivery_partner').order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    delivery_partners = User.objects.filter(delivery_profile__isnull=False)

    paginator = Paginator(orders, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/orders_list.html', {
        'page_obj': page_obj,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status or '',
        'delivery_partners': delivery_partners,
    })


@admin_required
def admin_order_detail(request, order_number):
    order = get_object_or_404(Order.objects.select_related('user', 'delivery_partner'), order_number=order_number)
    delivery_partners = User.objects.filter(delivery_profile__isnull=False)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign_delivery':
            partner_id = request.POST.get('delivery_partner_id')
            partner = get_object_or_404(User, pk=partner_id)
            order.delivery_partner = partner
            order.status = 'ASSIGNED'
            order.save()
            
            DeliveryAssignment.objects.update_or_create(
                order=order,
                defaults={'delivery_person': partner, 'status': 'ACCEPTED'}
            )
            order.add_status_history('ASSIGNED', comment=f"Assigned to delivery partner {partner.get_full_name() or partner.username}.", user=request.user)
            messages.success(request, f"Order assigned to {partner.get_full_name() or partner.username}.")

        elif action == 'update_status':
            new_status = request.POST.get('status')
            comment = request.POST.get('comment', '').strip() or 'Status updated by administrator.'
            if new_status not in dict(Order.STATUS_CHOICES):
                messages.error(request, "Invalid order status selected.")
            elif order.status == 'CANCELLED':
                messages.error(request, "This order is already cancelled and cannot be changed.")
            elif new_status == 'CANCELLED':
                # Same safe path as customer cancellation: restores stock + refunds prepaid payment
                order.cancel(reason=comment, user=request.user)
                messages.info(request, f"Order #{order.order_number} cancelled. Items returned to inventory.")
            else:
                order.add_status_history(new_status, comment=comment, user=request.user)
                messages.success(request, f"Order status updated to {order.get_status_display()}.")

        return redirect('dashboard:order_detail', order_number=order.order_number)

    return render(request, 'dashboard/order_detail.html', {
        'order': order,
        'delivery_partners': delivery_partners,
        'status_choices': Order.STATUS_CHOICES,
    })


# ==========================================
# USER MANAGEMENT
# ==========================================

@admin_required
def admin_customers_list(request):
    customers = User.objects.filter(is_staff=False, delivery_profile__isnull=True).annotate(orders_count=Count('orders')).order_by('-date_joined')
    return render(request, 'dashboard/customers_list.html', {'customers': customers})


@admin_required
def admin_delivery_staff_list(request):
    delivery_staff = User.objects.filter(delivery_profile__isnull=False).select_related('delivery_profile')
    
    if request.method == 'POST':
        # Create new delivery personnel account
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        vehicle_type = request.POST.get('vehicle_type', 'Bike')
        vehicle_number = request.POST.get('vehicle_number', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
            DeliveryProfile.objects.create(
                user=user,
                phone=phone,
                vehicle_type=vehicle_type,
                vehicle_number=vehicle_number,
                is_approved=True
            )
            messages.success(request, f"Delivery partner account '{username}' created successfully!")
            return redirect('dashboard:delivery_staff_list')

    return render(request, 'dashboard/delivery_staff.html', {'delivery_staff': delivery_staff})


# ==========================================
# COUPONS, RECIPES, EXPIRES & REVIEWS
# ==========================================

@admin_required
def admin_coupons_list(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '')
        discount_type = request.POST.get('discount_type', 'PERCENT')
        discount_value = Decimal(request.POST.get('discount_value', '10'))
        min_order_value = Decimal(request.POST.get('min_order_value', '0'))
        max_discount = Decimal(request.POST.get('max_discount', '0')) if request.POST.get('max_discount') else None
        valid_to = request.POST.get('valid_to')
        if valid_to:
            # <input type="datetime-local"> / "date" gives a naive value -> make it timezone-aware
            from django.utils.dateparse import parse_datetime, parse_date
            parsed = parse_datetime(valid_to)
            if parsed is None and parse_date(valid_to):
                parsed = datetime.datetime.combine(parse_date(valid_to), datetime.time(23, 59, 59))
            if parsed is not None and timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            valid_to = parsed

        if code and Coupon.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Coupon '{code}' already exists.")
        elif code and valid_to:
            Coupon.objects.create(
                code=code,
                description=description,
                discount_type=discount_type,
                discount_value=discount_value,
                min_order_value=min_order_value,
                max_discount=max_discount,
                valid_to=valid_to
            )
            messages.success(request, f"Coupon '{code}' created successfully!")
            return redirect('dashboard:coupons_list')

    return render(request, 'dashboard/coupons_list.html', {'coupons': coupons})


@admin_required
@require_POST
def admin_coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.info(request, "Coupon removed.")
    return redirect('dashboard:coupons_list')


@admin_required
def admin_recipes_list(request):
    recipes = Recipe.objects.annotate(ing_count=Count('ingredients')).order_by('name')
    return render(request, 'dashboard/recipes_list.html', {'recipes': recipes})


@admin_required
def admin_expiry_deals_list(request):
    deals = ExpiryRescueDeal.objects.select_related('product').order_by('expiry_date')
    products = Product.objects.filter(is_active=True, expiry_date__isnull=False)

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        discount_percent = int(request.POST.get('discount_percent', 50))
        prod = get_object_or_404(Product, pk=product_id)

        deal, _created = ExpiryRescueDeal.objects.update_or_create(
            product=prod,
            defaults={
                'rescue_discount_percent': discount_percent,
                'expiry_date': prod.expiry_date or (timezone.now().date() + timezone.timedelta(days=3)),
                'start_date': timezone.now().date(),
                'end_date': prod.expiry_date or (timezone.now().date() + timezone.timedelta(days=3)),
                'is_active': True
            }
        )
        # Let customers who wishlisted this product know about the rescue price
        from apps.core.notifications import notify_wishlist_rescue_deal
        notified = notify_wishlist_rescue_deal(deal)
        messages.success(request, f"Expiry Rescue Deal created for '{prod.name}' with {discount_percent}% off!"
                         + (f" {notified} wishlist customer(s) notified." if notified else ""))
        return redirect('dashboard:expiry_deals_list')

    return render(request, 'dashboard/expiry_deals_list.html', {
        'deals': deals,
        'products': products,
    })


@admin_required
def admin_reviews_list(request):
    reviews = Review.objects.select_related('product', 'user').order_by('-created_at')
    return render(request, 'dashboard/reviews_list.html', {'reviews': reviews})


@admin_required
@require_POST
def admin_review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    messages.info(request, "Review removed.")
    return redirect('dashboard:reviews_list')


# ==========================================
# ALERTS & SALES CSV EXPORT
# ==========================================

@admin_required
def admin_low_stock_expiry_alerts(request):
    low_stock = Product.objects.filter(is_active=True, stock_quantity__lte=10).order_by('stock_quantity')
    expiry_alerts = ExpiryRescueService.get_admin_expiry_alerts()

    return render(request, 'dashboard/alerts.html', {
        'low_stock': low_stock,
        'expiry_alerts': expiry_alerts,
    })


@admin_required
def admin_export_sales_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="SmartKart_Sales_Report_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Date', 'Customer Name', 'Status',
        'Subtotal (INR)', 'Discounts (INR)', 'Delivery Fee (INR)',
        'Grand Total (INR)', 'Payment Method', 'Payment Status', 'Delivery Partner'
    ])

    orders = Order.objects.select_related('user', 'delivery_partner').order_by('-created_at')
    for ord in orders:
        writer.writerow([
            ord.order_number,
            ord.created_at.strftime('%Y-%m-%d %H:%M'),
            ord.shipping_full_name,
            ord.get_status_display(),
            str(ord.subtotal),
            str(ord.total_savings),
            str(ord.delivery_fee),
            str(ord.grand_total),
            ord.get_payment_method_display(),
            ord.get_payment_status_display(),
            ord.delivery_partner.username if ord.delivery_partner else 'Unassigned'
        ])

    return response


# ==========================================
# ADDED: COMPLETING THE ADMIN CRUD SCREENS
# (category edit, coupon on/off, rescue-deal on/off, recipe add/edit/delete,
#  contact-message inbox, delivery partner availability)
# ==========================================

@admin_required
def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Category name is required.")
        elif Category.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            messages.error(request, f"Another category named '{name}' already exists.")
        else:
            category.name = name
            category.icon_class = request.POST.get('icon_class', '').strip() or 'bi-basket'
            category.description = request.POST.get('description', '')
            try:
                category.display_order = max(0, int(request.POST.get('display_order', category.display_order)))
            except ValueError:
                pass
            category.is_active = 'is_active' in request.POST
            category.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect('dashboard:categories_list')
    return render(request, 'dashboard/category_form.html', {'category': category})


@admin_required
@require_POST
def admin_coupon_toggle(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    messages.info(request, f"Coupon '{coupon.code}' is now {'ACTIVE' if coupon.is_active else 'PAUSED'}.")
    return redirect('dashboard:coupons_list')


@admin_required
@require_POST
def admin_expiry_deal_toggle(request, pk):
    deal = get_object_or_404(ExpiryRescueDeal, pk=pk)
    deal.is_active = not deal.is_active
    deal.save(update_fields=['is_active'])
    messages.info(request, f"Rescue deal for '{deal.product.name}' {'activated' if deal.is_active else 'deactivated'}.")
    return redirect('dashboard:expiry_deals_list')


def _save_recipe_from_post(request, recipe=None):
    """
    Shared create/update logic for recipes + their ingredient rows.
    Ingredient rows arrive as parallel lists: ing_name[], ing_qty[], ing_unit[], ing_product[], ing_notes[], ing_optional[]
    Returns (recipe, error_message).
    """
    name = request.POST.get('name', '').strip()
    if not name:
        return None, "Recipe name is required."
    if Recipe.objects.filter(name__iexact=name).exclude(pk=getattr(recipe, 'pk', None)).exists():
        return None, f"A recipe named '{name}' already exists."

    def _int(field, default):
        try:
            return max(1, int(request.POST.get(field, default)))
        except (TypeError, ValueError):
            return default

    names = request.POST.getlist('ing_name')
    qtys = request.POST.getlist('ing_qty')
    units = request.POST.getlist('ing_unit')
    product_ids = request.POST.getlist('ing_product')
    notes = request.POST.getlist('ing_notes')
    optional_rows = set(request.POST.getlist('ing_optional'))  # holds row indexes as strings

    rows = []
    for idx, ing_name in enumerate(names):
        ing_name = ing_name.strip()
        if not ing_name:
            continue
        try:
            qty = Decimal(qtys[idx] or '1')
        except Exception:
            return None, f"Invalid quantity for ingredient '{ing_name}'."
        rows.append({
            'ingredient_name': ing_name,
            'quantity_per_base_servings': qty,
            'unit': (units[idx] if idx < len(units) else 'g') or 'g',
            'product_id': (product_ids[idx] if idx < len(product_ids) else '') or None,
            'notes': (notes[idx] if idx < len(notes) else '')[:100],
            'is_optional': str(idx) in optional_rows,
        })
    if not rows:
        return None, "Add at least one ingredient."

    is_new = recipe is None
    recipe = recipe or Recipe()
    recipe.name = name
    if is_new:
        recipe.slug = ''  # auto-generated in Recipe.save()
    recipe.description = request.POST.get('description', '').strip() or name
    recipe.cuisine = request.POST.get('cuisine', 'Indian').strip() or 'Indian'
    recipe.diet_type = request.POST.get('diet_type', 'VEG') if request.POST.get('diet_type') in dict(Recipe.DIET_CHOICES) else 'VEG'
    recipe.difficulty = request.POST.get('difficulty', 'EASY') if request.POST.get('difficulty') in dict(Recipe.DIFFICULTY_CHOICES) else 'EASY'
    recipe.prep_time_minutes = _int('prep_time_minutes', 10)
    recipe.cook_time_minutes = _int('cook_time_minutes', 20)
    recipe.base_servings = _int('base_servings', 4)
    recipe.instructions = request.POST.get('instructions', '').strip() or "Prepare and cook as desired."
    recipe.is_featured = 'is_featured' in request.POST
    if request.FILES.get('image'):
        recipe.image = request.FILES['image']
    recipe.save()

    # Replace ingredient rows with what was submitted
    recipe.ingredients.all().delete()
    for row in rows:
        RecipeIngredient.objects.create(recipe=recipe, **row)
    return recipe, None


@admin_required
def admin_recipe_create(request):
    if request.method == 'POST':
        recipe, error = _save_recipe_from_post(request)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f"Recipe '{recipe.name}' created with {recipe.ingredients.count()} ingredients.")
            return redirect('dashboard:recipes_list')
    return render(request, 'dashboard/recipe_form.html', {
        'action': 'Add New Recipe',
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'diet_choices': Recipe.DIET_CHOICES,
        'difficulty_choices': Recipe.DIFFICULTY_CHOICES,
        'ingredient_rows': [None, None, None],
    })


@admin_required
def admin_recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == 'POST':
        recipe, error = _save_recipe_from_post(request, recipe)
        if error:
            messages.error(request, error)
            recipe = get_object_or_404(Recipe, pk=pk)
        else:
            messages.success(request, f"Recipe '{recipe.name}' updated.")
            return redirect('dashboard:recipes_list')
    return render(request, 'dashboard/recipe_form.html', {
        'action': 'Edit Recipe',
        'recipe': recipe,
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'diet_choices': Recipe.DIET_CHOICES,
        'difficulty_choices': Recipe.DIFFICULTY_CHOICES,
        'ingredient_rows': list(recipe.ingredients.select_related('product')) or [None],
    })


@admin_required
@require_POST
def admin_recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    name = recipe.name
    recipe.delete()
    messages.info(request, f"Recipe '{name}' deleted.")
    return redirect('dashboard:recipes_list')


@admin_required
def admin_contact_messages(request):
    from apps.core.models import ContactMessage
    show = request.GET.get('show', 'open')
    inbox = ContactMessage.objects.all()
    if show == 'open':
        inbox = inbox.filter(is_resolved=False)
    elif show == 'resolved':
        inbox = inbox.filter(is_resolved=True)
    return render(request, 'dashboard/contact_messages.html', {
        'inbox': inbox,
        'show': show,
        'open_count': ContactMessage.objects.filter(is_resolved=False).count(),
    })


@admin_required
@require_POST
def admin_contact_message_toggle(request, pk):
    from apps.core.models import ContactMessage
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_resolved = not msg.is_resolved
    msg.save(update_fields=['is_resolved'])
    messages.success(request, f"Message from {msg.name} marked as {'resolved' if msg.is_resolved else 'open'}.")
    return redirect(request.POST.get('next') or 'dashboard:contact_messages')


@admin_required
@require_POST
def admin_delivery_partner_toggle(request, pk):
    profile = get_object_or_404(DeliveryProfile, user_id=pk)
    profile.is_available = not profile.is_available
    profile.save(update_fields=['is_available'])
    messages.info(request, f"{profile.user.get_full_name() or profile.user.username} is now "
                           f"{'ON duty' if profile.is_available else 'OFF duty'}.")
    return redirect('dashboard:delivery_staff_list')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from apps.catalogue.models import Category, Product
from apps.smart_features.models import Recipe, ExpiryRescueDeal
from apps.core.models import Notification, ContactMessage
from apps.smart_features.expiry_service import ExpiryRescueService
from apps.smart_features.recommendation_engine import RecommendationEngine


def home_view(request):
    """
    Main landing page of SmartKart AI with rich sections and dynamic cards.
    """
    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    featured_products = Product.objects.filter(is_active=True, is_featured=True).select_related('category', 'brand')[:8]
    popular_products = Product.objects.filter(is_active=True).select_related('category', 'brand').order_by('-total_reviews', '-average_rating')[:8]
    
    # Active Expiry Rescue Deals
    rescue_deals = ExpiryRescueService.get_active_deals()[:4]
    
    # Featured Recipes for Recipe-to-Cart
    featured_recipes = Recipe.objects.filter(is_featured=True)[:4]
    if not featured_recipes.exists():
        featured_recipes = Recipe.objects.all()[:4]

    return render(request, 'core/home.html', {
        'categories': categories,
        'featured_products': featured_products,
        'popular_products': popular_products,
        'rescue_deals': rescue_deals,
        'featured_recipes': featured_recipes,
        'buy_again_products': RecommendationEngine.buy_again(request.user, limit=8),
    })


def about_view(request):
    return render(request, 'core/about.html')


def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if name and email and message_text:
            ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject or 'Customer Inquiry',
                message=message_text
            )
            messages.success(request, f"Thank you, {name}! Your message has been received. Our team will contact you shortly.")
            return redirect('core:contact')
        else:
            messages.error(request, "Please fill in all required fields.")

    return render(request, 'core/contact.html')


@login_required
def notifications_list_view(request):
    # Evaluate the list FIRST so unread items are still highlighted on this visit,
    # then mark everything as read for next time.
    notifications = list(Notification.objects.filter(user=request.user)[:100])
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
@require_POST
def mark_notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


# Custom Error Handlers
def custom_403_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def custom_404_view(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def custom_500_view(request):
    return render(request, 'errors/500.html', status=500)

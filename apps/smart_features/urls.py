from django.urls import path
from apps.smart_features import views

app_name = 'smart_features'

urlpatterns = [
    # Feature 1: AI Grocery List Scanner
    path('scanner/', views.scanner_view, name='scanner'),
    path('scanner/add-to-cart/', views.scanner_add_to_cart_view, name='scanner_add_to_cart'),

    # Feature 2: Monthly Budget Smart Cart
    path('budget/', views.budget_dashboard_view, name='budget_dashboard'),
    path('budget/update/', views.update_budget_settings_view, name='update_budget'),
    path('budget/swap-cheaper/', views.swap_cheaper_item_view, name='swap_cheaper_item'),

    # Feature 3: Recipe-to-Cart
    path('recipes/', views.recipe_list_view, name='recipe_list'),
    path('recipes/<slug:slug>/', views.recipe_detail_view, name='recipe_detail'),
    path('recipes/<slug:slug>/add-to-cart/', views.recipe_add_to_cart_view, name='recipe_add_to_cart'),

    # Feature 4: Expiry Rescue Deals
    path('expiry-deals/', views.expiry_deals_view, name='expiry_deals'),
    path('expiry-deals/<int:deal_id>/add/', views.expiry_deal_add_to_cart_view, name='expiry_add_to_cart'),

    # Feature 5: Smart Product Substitution
    path('substitute/<int:product_id>/', views.product_substitution_view, name='substitution_detail'),
    path('substitute/cart-swap/', views.substitute_in_cart_view, name='substitute_in_cart'),
]

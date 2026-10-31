from django.urls import path
from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_dashboard_view, name='admin_dashboard'),
    
    # Products & Catalogue
    path('products/', views.admin_products_list, name='products_list'),
    path('products/create/', views.admin_product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.admin_product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.admin_product_delete, name='product_delete'),
    
    path('categories/', views.admin_categories_list, name='categories_list'),
    path('categories/<int:pk>/delete/', views.admin_category_delete, name='category_delete'),
    path('categories/<int:pk>/edit/', views.admin_category_edit, name='category_edit'),
    path('inventory/', views.admin_inventory_view, name='inventory'),

    # Orders & Deliveries
    path('orders/', views.admin_orders_list, name='orders_list'),
    path('orders/<str:order_number>/', views.admin_order_detail, name='order_detail'),

    # Users
    path('customers/', views.admin_customers_list, name='customers_list'),
    path('delivery-staff/', views.admin_delivery_staff_list, name='delivery_staff_list'),
    path('delivery-staff/<int:pk>/toggle/', views.admin_delivery_partner_toggle, name='delivery_partner_toggle'),

    # Marketing, Smart Features & Content
    path('coupons/', views.admin_coupons_list, name='coupons_list'),
    path('coupons/<int:pk>/delete/', views.admin_coupon_delete, name='coupon_delete'),
    path('coupons/<int:pk>/toggle/', views.admin_coupon_toggle, name='coupon_toggle'),
    path('recipes/', views.admin_recipes_list, name='recipes_list'),
    path('recipes/create/', views.admin_recipe_create, name='recipe_create'),
    path('recipes/<int:pk>/edit/', views.admin_recipe_edit, name='recipe_edit'),
    path('recipes/<int:pk>/delete/', views.admin_recipe_delete, name='recipe_delete'),
    path('expiry-deals/', views.admin_expiry_deals_list, name='expiry_deals_list'),
    path('expiry-deals/<int:pk>/toggle/', views.admin_expiry_deal_toggle, name='expiry_deal_toggle'),
    path('reviews/', views.admin_reviews_list, name='reviews_list'),
    path('reviews/<int:pk>/delete/', views.admin_review_delete, name='review_delete'),

    # Alerts & Reports
    path('alerts/', views.admin_low_stock_expiry_alerts, name='alerts'),
    path('messages/', views.admin_contact_messages, name='contact_messages'),
    path('messages/<int:pk>/toggle/', views.admin_contact_message_toggle, name='contact_message_toggle'),
    path('export/sales-csv/', views.admin_export_sales_csv, name='export_sales_csv'),
]

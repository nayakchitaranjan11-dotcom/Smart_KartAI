from django.urls import path
from apps.delivery import views

app_name = 'delivery'

urlpatterns = [
    path('', views.delivery_dashboard_view, name='dashboard'),
    path('order/<str:order_number>/', views.delivery_order_detail_view, name='order_detail'),
    path('order/<str:order_number>/update-status/', views.update_delivery_status_view, name='update_status'),
    path('completed/', views.completed_deliveries_view, name='completed_orders'),
    path('profile/', views.delivery_profile_view, name='profile'),
]

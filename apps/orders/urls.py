from django.urls import path
from apps.orders import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('confirmation/<str:order_number>/', views.order_confirmation_view, name='confirmation'),
    path('history/', views.order_history_view, name='order_history'),
    path('<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('<str:order_number>/tracking/', views.order_tracking_view, name='order_tracking'),
    path('<str:order_number>/cancel/', views.cancel_order_view, name='cancel_order'),
    path('<str:order_number>/invoice/', views.download_invoice_view, name='download_invoice'),
    path('<str:order_number>/status.json', views.order_status_api, name='order_status_api'),
    path('<str:order_number>/reorder/', views.reorder_view, name='reorder'),
]

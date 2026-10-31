from django.urls import path
from apps.catalogue import views

app_name = 'catalogue'

urlpatterns = [
    path('', views.product_list_view, name='product_list'),
    path('category/<slug:slug>/', views.category_products_view, name='category_products'),
    path('search/', views.product_search_view, name='product_search'),
    path('api/suggestions/', views.search_suggestions_api, name='search_suggestions'),
    path('<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('<slug:slug>/review/', views.add_review_view, name='add_review'),
]

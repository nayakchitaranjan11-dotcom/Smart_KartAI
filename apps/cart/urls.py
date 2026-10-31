from django.urls import path
from apps.cart import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail_view, name='cart_detail'),
    path('add/', views.add_to_cart_view, name='add_to_cart'),
    path('update/<int:item_id>/', views.update_cart_item_view, name='update_item'),
    path('remove/<int:item_id>/', views.remove_cart_item_view, name='remove_item'),
    path('apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon_view, name='remove_coupon'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist_view, name='toggle_wishlist'),
    # Instant (AJAX) cart API used by the ADD -> [- 1 +] stepper buttons
    path('api/state/', views.cart_state_api, name='api_state'),
    path('api/set/', views.cart_set_quantity_api, name='api_set_quantity'),
]

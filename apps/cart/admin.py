from django.contrib import admin

from apps.cart.models import Coupon, Cart, CartItem, Wishlist, WishlistItem


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_value', 'max_discount',
                    'valid_from', 'valid_to', 'used_count', 'usage_limit', 'is_active')
    list_filter = ('discount_type', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('code', 'description')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'coupon', 'updated_at')
    search_fields = ('user__username', 'session_key')
    inlines = [CartItemInline]


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    inlines = [WishlistItemInline]

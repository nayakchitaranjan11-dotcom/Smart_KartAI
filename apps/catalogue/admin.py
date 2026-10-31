from django.contrib import admin

from apps.catalogue.models import Category, Brand, Product, ProductImage, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_class', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'unit', 'selling_price', 'original_price',
                    'stock_quantity', 'expiry_date', 'is_featured', 'is_active')
    list_filter = ('category', 'brand', 'is_featured', 'is_active')
    list_editable = ('selling_price', 'stock_quantity', 'is_featured', 'is_active')
    search_fields = ('name', 'description', 'nutritional_tags')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('average_rating', 'total_reviews', 'created_at', 'updated_at')
    inlines = [ProductImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'headline', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_verified_purchase')
    search_fields = ('product__name', 'user__username', 'comment')

from django.contrib import admin

from apps.smart_features.models import (
    MonthlyBudget, Recipe, RecipeIngredient, GroceryScan, GroceryScanItem, ExpiryRescueDeal
)


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'month', 'year', 'budget_amount', 'warning_threshold_percent')
    list_filter = ('year', 'month')
    search_fields = ('user__username',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('product',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'cuisine', 'diet_type', 'difficulty', 'base_servings', 'is_featured')
    list_filter = ('diet_type', 'difficulty', 'cuisine', 'is_featured')
    search_fields = ('name', 'cuisine')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RecipeIngredientInline]


class GroceryScanItemInline(admin.TabularInline):
    model = GroceryScanItem
    extra = 0


@admin.register(GroceryScan)
class GroceryScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'is_ocr_available', 'created_at')
    inlines = [GroceryScanItemInline]


@admin.register(ExpiryRescueDeal)
class ExpiryRescueDealAdmin(admin.ModelAdmin):
    list_display = ('product', 'rescue_discount_percent', 'rescue_price', 'expiry_date',
                    'end_date', 'rescued_count', 'is_active')
    list_filter = ('is_active',)
    list_editable = ('is_active',)
    search_fields = ('product__name',)

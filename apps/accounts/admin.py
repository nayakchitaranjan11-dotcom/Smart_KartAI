from django.contrib import admin

from apps.accounts.models import CustomerProfile, DeliveryProfile, Address

# Branding for the built-in Django admin site (/admin/)
admin.site.site_header = "SmartKart AI - Django Administration"
admin.site.site_title = "SmartKart AI Admin"
admin.site.index_title = "Database Management (all SmartKart tables)"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'monthly_budget', 'budget_warning_threshold', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'vehicle_type', 'vehicle_number', 'is_available', 'is_approved', 'rating', 'total_deliveries')
    list_filter = ('is_available', 'is_approved', 'vehicle_type')
    list_editable = ('is_available', 'is_approved')
    search_fields = ('user__username', 'phone', 'vehicle_number')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'address_type', 'city', 'postal_code', 'is_default')
    list_filter = ('address_type', 'city', 'is_default')
    search_fields = ('full_name', 'user__username', 'street_address', 'postal_code')

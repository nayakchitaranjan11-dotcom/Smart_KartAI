from django.contrib import admin

from apps.orders.models import Order, OrderItem, OrderStatusHistory, Payment, DeliveryAssignment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'grand_total', 'payment_method',
                    'payment_status', 'delivery_partner', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_status', 'delivery_slot')
    search_fields = ('order_number', 'user__username', 'shipping_full_name', 'shipping_phone')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('payment_method', 'status')
    search_fields = ('transaction_id', 'order__order_number')


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_person', 'status', 'assigned_at', 'delivered_at')
    list_filter = ('status',)

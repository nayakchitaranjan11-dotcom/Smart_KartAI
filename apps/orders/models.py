from django.db import models, transaction
from django.db.models import F
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid
from apps.catalogue.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('PLACED', 'Order Placed'),
        ('CONFIRMED', 'Confirmed'),
        ('PACKING', 'Packing in Warehouse'),
        ('READY_FOR_PICKUP', 'Ready for Pickup'),
        ('ASSIGNED', 'Delivery Partner Assigned'),
        ('PICKED_UP', 'Picked Up'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery (Simulated)'),
        ('UPI', 'UPI / QR Payment (Academic Simulation)'),
        ('CARD', 'Credit / Debit Card (Academic Simulation)'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid (Simulated)'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    DELIVERY_SLOT_CHOICES = [
        ('EXPRESS_15MIN', 'Instant 15-30 Min Express Delivery'),
        ('SLOT_MORNING', 'Morning Slot (7:00 AM - 9:00 AM)'),
        ('SLOT_AFTERNOON', 'Afternoon Slot (12:00 PM - 2:00 PM)'),
        ('SLOT_EVENING', 'Evening Slot (5:00 PM - 7:00 PM)'),
        ('SLOT_NIGHT', 'Night Slot (8:00 PM - 10:00 PM)'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PLACED')

    # Shipping Address Snapshot
    shipping_full_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=15)
    shipping_street = models.TextField()
    shipping_landmark = models.CharField(max_length=100, blank=True)
    shipping_city = models.CharField(max_length=50)
    shipping_state = models.CharField(max_length=50)
    shipping_postal_code = models.CharField(max_length=10)

    # Delivery Preferences
    delivery_slot = models.CharField(max_length=30, choices=DELIVERY_SLOT_CHOICES, default='EXPRESS_15MIN')
    order_notes = models.TextField(blank=True)

    # Financial Snapshots
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    product_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='COD')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=64, blank=True)

    # Delivery partner
    delivery_partner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')

    # Cancellation
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            now_str = timezone.now().strftime('%Y%m%d')
            uid_str = uuid.uuid4().hex[:6].upper()
            self.order_number = f"SK-{now_str}-{uid_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} ({self.user.username}) - ₹{self.grand_total}"

    @property
    def is_cancellable(self):
        return self.status in ['PLACED', 'CONFIRMED', 'PACKING']

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_savings(self):
        return self.product_discount + self.coupon_discount

    def add_status_history(self, new_status, comment="", user=None):
        self.status = new_status
        if new_status == 'DELIVERED' and not self.delivered_at:
            self.delivered_at = timezone.now()
            if self.payment_method == 'COD':
                self.payment_status = 'PAID'
            if self.delivery_partner and hasattr(self.delivery_partner, 'delivery_profile'):
                profile = self.delivery_partner.delivery_profile
                profile.total_deliveries += 1
                profile.save()
        elif new_status == 'CANCELLED':
            self.cancelled_at = timezone.now()
        self.save()

        OrderStatusHistory.objects.create(
            order=self,
            status=new_status,
            comment=comment,
            updated_by=user
        )

        # In-app notification for customer (and rider on assignment)
        from apps.core.notifications import notify_order_status
        notify_order_status(self, new_status)

    def cancel(self, reason="", user=None):
        """
        Cancels the order safely (used by both customer and admin):
          1. returns every item to inventory,
          2. marks prepaid (UPI/Card) payments as REFUNDED (simulated),
          3. records status history + notification.
        Returns False if the order was already cancelled.
        """
        if self.status == 'CANCELLED':
            return False
        with transaction.atomic():
            for item in self.items.all():
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(
                        stock_quantity=F('stock_quantity') + item.quantity
                    )
            self.cancellation_reason = reason or "Cancelled"
            if self.payment_status == 'PAID':
                self.payment_status = 'REFUNDED'
                Payment.objects.filter(order=self).update(status='REFUNDED')
            self.add_status_history('CANCELLED', comment=f"Reason: {self.cancellation_reason}", user=user)
        return True

    @property
    def progress_percent(self):
        """0-100 progress used by the live tracking map."""
        flow = ['PLACED', 'CONFIRMED', 'PACKING', 'READY_FOR_PICKUP', 'ASSIGNED',
                'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED']
        if self.status not in flow:
            return 0
        return int(round(flow.index(self.status) / (len(flow) - 1) * 100))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=200)
    product_unit = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in #{self.order.order_number}"

    @property
    def savings(self):
        orig_total = self.original_price * Decimal(str(self.quantity))
        return max(Decimal('0.00'), orig_total - self.total_price)


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=25, choices=Order.STATUS_CHOICES)
    comment = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Order #{self.order.order_number} -> {self.get_status_display()} at {self.created_at.strftime('%d %b %H:%M')}"


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_record')
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=20, choices=Order.PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Order.PAYMENT_STATUS_CHOICES, default='PAID')
    simulation_notes = models.CharField(max_length=255, default="Academic Simulation - No actual transaction processed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for #{self.order.order_number} - ₹{self.amount} ({self.status})"


class DeliveryAssignment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Acceptance'),
        ('ACCEPTED', 'Accepted'),
        ('PICKED_UP', 'Picked Up'),
        ('DELIVERED', 'Delivered'),
        ('REJECTED', 'Rejected'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_assignment')
    delivery_person = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Assignment for Order #{self.order.order_number} -> {self.delivery_person.username}"

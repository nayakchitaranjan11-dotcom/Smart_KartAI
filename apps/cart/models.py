from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from apps.catalogue.models import Product


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENT', 'Percentage Discount'),
        ('FLAT', 'Flat Amount Discount'),
    ]

    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='PERCENT')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage (e.g. 10.00 for 10%) or Flat Amount in ₹")
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Max discount limit for percentage coupons in ₹")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1000, help_text="Maximum number of redemptions")
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()} - {self.discount_value})"

    def is_valid(self, subtotal=Decimal('0.00')):
        now = timezone.now()
        if not self.is_active:
            return False, "This coupon is currently inactive."
        if now < self.valid_from:
            return False, "This coupon has not started yet."
        if now > self.valid_to:
            return False, "This coupon has expired."
        if self.used_count >= self.usage_limit:
            return False, "This coupon usage limit has been reached."
        if subtotal < self.min_order_value:
            return False, f"Minimum order value of ₹{self.min_order_value} required to apply this coupon."
        return True, "Coupon applied successfully!"

    def calculate_discount(self, subtotal):
        valid, msg = self.is_valid(subtotal)
        if not valid:
            return Decimal('0.00')

        if self.discount_type == 'PERCENT':
            discount = (subtotal * self.discount_value) / Decimal('100.00')
            if self.max_discount and discount > self.max_discount:
                discount = self.max_discount
        else:
            discount = self.discount_value

        return min(discount, subtotal).quantize(Decimal('0.01'))


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username} (Items: {self.total_items})"
        return f"Guest Cart {self.session_key} (Items: {self.total_items})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        total = sum(item.total_price for item in self.items.all())
        return Decimal(str(total)).quantize(Decimal('0.01'))

    @property
    def original_subtotal(self):
        total = sum(item.original_total_price for item in self.items.all())
        return Decimal(str(total)).quantize(Decimal('0.01'))

    @property
    def product_savings(self):
        return max(Decimal('0.00'), self.original_subtotal - self.subtotal)

    @property
    def coupon_discount(self):
        if self.coupon:
            return self.coupon.calculate_discount(self.subtotal)
        return Decimal('0.00')

    @property
    def total_savings(self):
        return self.product_savings + self.coupon_discount

    @property
    def delivery_fee(self):
        if self.subtotal == 0:
            return Decimal('0.00')
        # Free delivery for orders above ₹499, else ₹30
        if self.subtotal >= Decimal('499.00'):
            return Decimal('0.00')
        return Decimal('30.00')

    @property
    def grand_total(self):
        if self.subtotal == 0:
            return Decimal('0.00')
        total = (self.subtotal - self.coupon_discount) + self.delivery_fee
        return max(Decimal('0.00'), total).quantize(Decimal('0.01'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def unit_price(self):
        # Check if there is an active expiry deal for this product
        if hasattr(self.product, 'expiry_deal') and self.product.expiry_deal.is_currently_active:
            return self.product.expiry_deal.rescue_price
        return self.product.selling_price

    @property
    def total_price(self):
        return (self.unit_price * Decimal(str(self.quantity))).quantize(Decimal('0.01'))

    @property
    def original_total_price(self):
        return (self.product.original_price * Decimal(str(self.quantity))).quantize(Decimal('0.01'))

    @property
    def savings(self):
        return max(Decimal('0.00'), self.original_total_price - self.total_price)


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"

    @property
    def total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_entries')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s wishlist"

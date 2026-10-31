from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5000.00'))
    budget_warning_threshold = models.IntegerField(default=80, help_text="Percentage of budget at which to trigger warnings")
    budget_reset_day = models.IntegerField(default=1, help_text="Day of month when budget resets (1-28)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Customer Profile"


class DeliveryProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_profile')
    phone = models.CharField(max_length=15)
    vehicle_type = models.CharField(max_length=50, default='Bike / Scooter')
    vehicle_number = models.CharField(max_length=20, blank=True)
    driving_license = models.CharField(max_length=50, blank=True)
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('5.00'))
    total_deliveries = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Delivery Partner)"


class Address(models.Model):
    ADDRESS_TYPES = [
        ('HOME', 'Home'),
        ('WORK', 'Work'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='HOME')
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    street_address = models.TextField(help_text="House/Flat No., Building, Street Area")
    landmark = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50, default='New Delhi')
    state = models.CharField(max_length=50, default='Delhi')
    postal_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.street_address[:30]}, {self.city} ({self.get_address_type_display()})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        if not hasattr(instance, 'customer_profile') and not hasattr(instance, 'delivery_profile'):
            CustomerProfile.objects.create(user=instance)

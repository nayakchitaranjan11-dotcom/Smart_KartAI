from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal
import datetime


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    icon_class = models.CharField(max_length=50, default='bi-basket', help_text="Bootstrap icon class e.g. bi-basket, bi-egg-fried")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def active_products_count(self):
        return self.products.filter(is_active=True).count()


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="MRP in Rupees")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Discounted price in Rupees")
    unit = models.CharField(max_length=50, help_text="e.g. 1 kg, 500 g, 1 L, 1 Pack, 250 g")
    unit_value = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1.00'), help_text="Numeric unit value for comparison (e.g. 1.0 for 1kg, 0.5 for 500g)")
    unit_type = models.CharField(max_length=20, default='kg', help_text="kg, g, l, ml, pack, piece")
    stock_quantity = models.PositiveIntegerField(default=50)
    reorder_level = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True, help_text="Applicable for perishable and fresh goods")
    nutritional_tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated e.g. Organic, High Protein, Gluten Free, Dairy Free")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    total_reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            candidate_slug = base_slug
            idx = 1
            while Product.objects.filter(slug=candidate_slug).exclude(pk=self.pk).exists():
                candidate_slug = f"{base_slug}-{idx}"
                idx += 1
            self.slug = candidate_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.unit}) - ₹{self.selling_price}"

    @property
    def discount_percent(self):
        if self.original_price > 0 and self.selling_price < self.original_price:
            discount = ((self.original_price - self.selling_price) / self.original_price) * 100
            return int(round(discount))
        return 0

    @property
    def savings(self):
        if self.original_price > self.selling_price:
            return self.original_price - self.selling_price
        return Decimal('0.00')

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0 and not self.is_expired

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.reorder_level

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_to_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def tags_list(self):
        if self.nutritional_tags:
            return [t.strip() for t in self.nutritional_tags.split(',') if t.strip()]
        return []

    def update_rating_metrics(self):
        reviews = self.reviews.all()
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.average_rating = Decimal(str(round(avg, 2)))
            self.total_reviews = reviews.count()
        else:
            self.average_rating = Decimal('0.00')
            self.total_reviews = 0
        self.save(update_fields=['average_rating', 'total_reviews'])


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='products/gallery/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} Stars") for i in range(1, 6)])
    headline = models.CharField(max_length=150, blank=True)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user', 'order')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.update_rating_metrics()

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal
import datetime
from apps.catalogue.models import Product


def current_month():
    """Callable default -> evaluated at row-creation time (not once at server start)."""
    return timezone.now().month


def current_year():
    return timezone.now().year


class MonthlyBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_budgets')
    month = models.PositiveSmallIntegerField(default=current_month)
    year = models.PositiveSmallIntegerField(default=current_year)
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5000.00'))
    warning_threshold_percent = models.PositiveIntegerField(default=80, help_text="Percentage threshold for alert (e.g. 80%)")
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.username} Budget ({self.month}/{self.year}) - ₹{self.budget_amount}"

    @property
    def warning_threshold_amount(self):
        return (self.budget_amount * Decimal(str(self.warning_threshold_percent))) / Decimal('100.00')


class Recipe(models.Model):
    DIET_CHOICES = [
        ('VEG', 'Vegetarian'),
        ('NON_VEG', 'Non-Vegetarian'),
        ('VEGAN', 'Vegan'),
        ('EGG', 'Eggetarian'),
    ]

    DIFFICULTY_CHOICES = [
        ('EASY', 'Easy (Under 20 mins)'),
        ('MEDIUM', 'Medium (20-45 mins)'),
        ('HARD', 'Hard (45+ mins)'),
    ]

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    image = models.ImageField(upload_to='recipes/', blank=True, null=True)
    description = models.TextField()
    cuisine = models.CharField(max_length=50, default='Indian', help_text="e.g. North Indian, South Indian, Italian, Continental")
    diet_type = models.CharField(max_length=10, choices=DIET_CHOICES, default='VEG')
    prep_time_minutes = models.PositiveIntegerField(default=10)
    cook_time_minutes = models.PositiveIntegerField(default=20)
    base_servings = models.PositiveIntegerField(default=4, help_text="Number of people this recipe serves by default")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='EASY')
    instructions = models.TextField(help_text="Step-by-step cooking instructions (newline separated or numbered)")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_diet_type_display()} - {self.cuisine})"

    @property
    def total_time_minutes(self):
        return self.prep_time_minutes + self.cook_time_minutes

    def get_instructions_list(self):
        return [line.strip() for line in self.instructions.split('\n') if line.strip()]

    def calculate_cost_for_servings(self, servings=4):
        """Shopping cost for the given servings = sum(pack price x packs needed)."""
        from apps.smart_features.units import packs_needed
        total_cost = Decimal('0.00')
        for item in self.ingredients.all():
            if item.product:
                packs = packs_needed(item.get_scaled_quantity(servings), item.unit, item.product)
                total_cost += item.product.selling_price * packs
        return total_cost.quantize(Decimal('0.01'))


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipe_mappings')
    ingredient_name = models.CharField(max_length=100)
    quantity_per_base_servings = models.DecimalField(max_digits=8, decimal_places=2, help_text="Quantity for recipe.base_servings")
    unit = models.CharField(max_length=30, default='g', help_text="g, kg, ml, tbsp, tsp, piece, pack")
    is_optional = models.BooleanField(default=False)
    notes = models.CharField(max_length=100, blank=True, help_text="e.g. finely chopped, soaked overnight")

    def __str__(self):
        return f"{self.ingredient_name} ({self.quantity_per_base_servings} {self.unit}) for {self.recipe.name}"

    def get_scaled_quantity(self, target_servings):
        ratio = Decimal(str(target_servings)) / Decimal(str(self.recipe.base_servings))
        scaled = self.quantity_per_base_servings * ratio
        return scaled.quantize(Decimal('0.01'))


class GroceryScan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='grocery_scans')
    image = models.ImageField(upload_to='scans/')
    raw_extracted_text = models.TextField(blank=True)
    is_ocr_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default='PARSED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan #{self.pk} - {self.created_at.strftime('%d %b %Y %H:%M')}"


class GroceryScanItem(models.Model):
    scan = models.ForeignKey(GroceryScan, on_delete=models.CASCADE, related_name='parsed_items')
    raw_line = models.CharField(max_length=200)
    parsed_item_name = models.CharField(max_length=150)
    parsed_quantity = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.00'))
    parsed_unit = models.CharField(max_length=30, blank=True, default='pack')
    matched_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_matches')
    confidence_score = models.FloatField(default=0.0, help_text="Fuzzy matching confidence percentage 0 - 100")
    is_approved = models.BooleanField(default=True)
    suggested_action = models.CharField(max_length=50, default='READY')

    def __str__(self):
        return f"{self.raw_line} -> {self.matched_product.name if self.matched_product else 'Unmatched'} ({self.confidence_score}%)"


class ExpiryRescueDeal(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='expiry_deal')
    rescue_discount_percent = models.PositiveIntegerField(default=50, help_text="Rescue discount e.g. 50% off")
    rescue_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Discounted rescue selling price in ₹")
    expiry_date = models.DateField(help_text="Product Expiry Date")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    rescued_count = models.PositiveIntegerField(default=0, help_text="Total units rescued through purchases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return f"Rescue Deal: {self.product.name} (Exp: {self.expiry_date}, ₹{self.rescue_price})"

    @property
    def days_remaining(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def is_currently_active(self):
        today = timezone.now().date()
        return (
            self.is_active and
            self.product.stock_quantity > 0 and
            today <= self.expiry_date and
            self.start_date <= today <= self.end_date
        )

    @property
    def urgency_level(self):
        days = self.days_remaining
        if days <= 1:
            return 'danger'  # Red: expires within 1 day
        elif days <= 3:
            return 'warning' # Orange: expires within 3 days
        elif days <= 7:
            return 'info'    # Yellow: expires within 7 days
        return 'success'

    def save(self, *args, **kwargs):
        if not self.rescue_price or self.rescue_price >= self.product.selling_price:
            discount = Decimal(str(self.rescue_discount_percent)) / Decimal('100.00')
            self.rescue_price = (self.product.original_price * (Decimal('1.00') - discount)).quantize(Decimal('0.01'))
        if not self.end_date:
            self.end_date = self.expiry_date
        super().save(*args, **kwargs)

from django.db import models
from django.conf import settings

# Create your models here.


class Product(models.Model):
	CATEGORY_BOTTLED = "bottled"
	CATEGORY_MEAL = "meal"
	CATEGORY_SNACK = "snack"
	CATEGORY_DRINK = "drink"

	CATEGORY_CHOICES = [
		(CATEGORY_BOTTLED, "Bottled Chili Garlic"),
		(CATEGORY_MEAL, "Chili Garlic Meals"),
		(CATEGORY_SNACK, "Snack"),
		(CATEGORY_DRINK, "Drinks"),
	]

	name = models.CharField(max_length=100)
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_BOTTLED)
	price = models.DecimalField(max_digits=8, decimal_places=2)
	stock = models.PositiveIntegerField(default=0)
	image = models.ImageField(upload_to="products/", blank=True, null=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:  # type: ignore[override]
		return self.name


class Order(models.Model):
	STATUS_PENDING = "pending"
	STATUS_PREPARING = "preparing"
	STATUS_READY_FOR_PICKUP = "ready_for_pickup"
	STATUS_COMPLETED = "completed"
	STATUS_CANCELLED = "cancelled"

	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_PREPARING, "Preparing"),
		(STATUS_READY_FOR_PICKUP, "Ready for pick up"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_CANCELLED, "Cancelled"),
	]

	customer = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="orders",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	def __str__(self) -> str:  # type: ignore[override]
		return f"Order #{self.pk} by {self.customer}"


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=8, decimal_places=2)
	addons = models.CharField(max_length=255, blank=True)

	def line_total(self) -> float:
		return float(self.quantity) * float(self.unit_price)

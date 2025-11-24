from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Order, OrderItem

# Register your models here.


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("image_thumb", "name", "price", "is_active", "created_at")
	list_filter = ("is_active",)
	search_fields = ("name",)

	def image_thumb(self, obj):  # pragma: no cover - simple admin display helper
		if obj.image:
			return format_html(
				'<img src="{}" style="width:40px; height:40px; object-fit:cover; border-radius:4px;" />',
				obj.image.url,
			)
		return "—"

	image_thumb.short_description = "Image"


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "customer", "status", "total_amount", "created_at")
	list_filter = ("status", "created_at")
	search_fields = ("customer__username", "id")
	inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ("order", "product", "quantity", "unit_price")

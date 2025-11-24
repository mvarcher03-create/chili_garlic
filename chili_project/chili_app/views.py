from decimal import Decimal
from datetime import timedelta
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone

from .forms import CustomerRegistrationForm, ProductForm, ProfileForm
from .models import Product, Order, OrderItem

# Create your views here.


def home(request):
	return render(request, "home.html")


def login_view(request):
	if request.user.is_authenticated:
		if request.user.is_staff:
			return redirect("admin_dashboard")
		return redirect("customer_dashboard")

	if request.method == "POST":
		username = request.POST.get("username")
		password = request.POST.get("password")
		remember_me = request.POST.get("remember_me")
		user = authenticate(request, username=username, password=password)
		# On Render we might not have a way to run createsuperuser from the shell.
		# Allow bootstrapping the first admin account using environment variables.
		if user is None:
			initial_admin_username = os.getenv("DJANGO_INITIAL_ADMIN_USERNAME")
			initial_admin_password = os.getenv("DJANGO_INITIAL_ADMIN_PASSWORD")
			if (
				initial_admin_username
				and initial_admin_password
				and not User.objects.filter(is_superuser=True).exists()
				and username == initial_admin_username
				and password == initial_admin_password
			):
				user = User.objects.create_superuser(
					username=initial_admin_username,
					email="",
					password=initial_admin_password,
				)
		if user is not None:
			login(request, user)
			if remember_me:
				request.session.set_expiry(60 * 60 * 24 * 14)
			else:
				request.session.set_expiry(0)
			if user.is_staff:
				return redirect("admin_dashboard")
			return redirect("customer_dashboard")
		messages.error(request, "Invalid username or password.")

	return render(request, "login.html")


def logout_view(request):
	logout(request)
	return redirect("home")


def register_view(request):
	if request.user.is_authenticated:
		if request.user.is_staff:
			return redirect("admin_dashboard")
		return redirect("customer_dashboard")

	if request.method == "POST":
		form = CustomerRegistrationForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "Account created successfully. You can now log in.")
			return redirect("login")
	else:
		form = CustomerRegistrationForm()

	return render(request, "register.html", {"form": form})


@login_required
def admin_dashboard(request):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	now = timezone.now()
	today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
	week_start = today_start - timedelta(days=6)

	today_orders_count = Order.objects.filter(created_at__gte=today_start).count()

	week_completed_orders = Order.objects.filter(
		created_at__gte=week_start,
		status=Order.STATUS_COMPLETED,
	)
	week_revenue = week_completed_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

	top_item = (
		OrderItem.objects.filter(
			order__created_at__gte=week_start,
			order__status=Order.STATUS_COMPLETED,
		)
		.values("product__name")
		.annotate(total_qty=Sum("quantity"))
		.order_by("-total_qty")
		.first()
	)
	top_product_name = top_item["product__name"] if top_item else ""
	top_product_quantity = top_item["total_qty"] if top_item else 0

	recent_orders = (
		Order.objects.select_related("customer")
		.order_by("-created_at")
		.prefetch_related("items__product")[:10]
	)

	context = {
		"today_orders_count": today_orders_count,
		"week_revenue": week_revenue,
		"top_product_name": top_product_name,
		"top_product_quantity": top_product_quantity,
		"recent_orders": recent_orders,
	}
	return render(request, "admin_dashboard.html", context)


@login_required
def customer_dashboard(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	total_orders = Order.objects.filter(customer=request.user).count()
	pending_orders = Order.objects.filter(customer=request.user, status=Order.STATUS_PENDING).count()
	total_spent = (
		Order.objects.filter(customer=request.user)
		.aggregate(total=Sum("total_amount"))["total"]
		or Decimal("0")
	)
	order_history = (
		Order.objects.filter(customer=request.user)
		.order_by("-created_at")
		.prefetch_related("items__product")
	)
	products = Product.objects.filter(is_active=True, stock__gt=0).order_by("category", "name")

	context = {
		"total_orders": total_orders,
		"pending_orders": pending_orders,
		"total_spent": total_spent,
		"order_history": order_history,
		"products": products,
	}
	return render(request, "customer_dashboard.html", context)


@login_required
def customer_order_now(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	products = Product.objects.filter(is_active=True).order_by("category", "name")

	return render(request, "order_now.html", {"products": products})


@login_required
def customer_product_detail(request, product_id: int):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	product = get_object_or_404(Product, pk=product_id, is_active=True)

	return render(request, "view_product.html", {"product": product})


@login_required
def customer_cart_add(request, product_id: int):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	product = get_object_or_404(Product, pk=product_id, is_active=True)

	if request.method == "POST":
		# Quantity
		try:
			quantity = int(request.POST.get("quantity", "1") or "1")
		except ValueError:
			quantity = 1
		if quantity < 1:
			quantity = 1

		# Check stock availability
		available = product.stock or 0
		if available <= 0:
			messages.error(request, f"{product.name} is currently out of stock.")
			return redirect("customer_order_now")

		cart = request.session.get("cart", {})
		key = str(product.id)
		try:
			current_qty = int(cart.get(key, 0) or 0)
		except ValueError:
			current_qty = 0

		# Prevent cart quantity from exceeding available stock
		if current_qty + quantity > available:
			messages.error(
				request,
				f"Only {available} × {product.name} left in stock.",
			)
			return redirect("customer_order_now")

		# Optional add-ons / notes
		addons = (request.POST.get("addons") or "").strip()

		cart[key] = current_qty + quantity
		request.session["cart"] = cart

		if addons:
			cart_addons = request.session.get("cart_addons", {})
			cart_addons[key] = addons
			request.session["cart_addons"] = cart_addons

		messages.success(request, f"Added {quantity} × {product.name} to your cart.")

		next_url = request.POST.get("next")
		if next_url:
			return redirect(next_url)

	return redirect("customer_order_now")


@login_required
def customer_cart_view(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	cart = request.session.get("cart", {})
	cart_addons = request.session.get("cart_addons", {})
	ids = [int(pk) for pk in cart.keys()]
	products = Product.objects.filter(id__in=ids)

	items = []
	total = Decimal("0")
	for product in products:
		qty = int(cart.get(str(product.id), 0))
		if qty <= 0:
			continue
		line_total = product.price * qty
		total += line_total
		addons = cart_addons.get(str(product.id), "")
		items.append({"product": product, "quantity": qty, "line_total": line_total, "addons": addons})

	context = {"items": items, "total": total}
	return render(request, "cart.html", context)


@login_required
def customer_cart_update(request, product_id: int):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	product = get_object_or_404(Product, pk=product_id)

	if request.method != "POST":
		return redirect("customer_cart")

	cart = request.session.get("cart", {})
	key = str(product_id)

	# If not in cart, nothing to update
	if key not in cart:
		return redirect("customer_cart")

	op = (request.POST.get("op") or "").strip().lower()

	try:
		qty = int(cart.get(key, 0) or 0)
	except ValueError:
		qty = 0

	if op == "inc":
		# Increase quantity only if it does not exceed available stock
		available = product.stock or 0
		if available <= 0:
			messages.error(request, "No more stock available for this product.")
		elif qty + 1 > available:
			messages.error(
				request,
				f"Only {available} × {product.name} left in stock.",
			)
		else:
			qty += 1
	elif op == "dec":
		qty -= 1

	if qty <= 0:
		# Remove item (and its addons) when quantity reaches 0
		cart.pop(key, None)
		cart_addons = request.session.get("cart_addons", {})
		if key in cart_addons:
			cart_addons.pop(key, None)
			request.session["cart_addons"] = cart_addons
	else:
		cart[key] = qty

	request.session["cart"] = cart
	return redirect("customer_cart")


@login_required
def customer_checkout(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	cart = request.session.get("cart", {})
	cart_addons = request.session.get("cart_addons", {})
	if not cart:
		messages.error(request, "Your cart is empty.")
		return redirect("customer_cart")

	ids = [int(pk) for pk in cart.keys()]
	products = Product.objects.filter(id__in=ids)

	if not products:
		messages.error(request, "Your cart is empty.")
		return redirect("customer_cart")

	if request.method == "GET":
		items = []
		total = Decimal("0")
		for product in products:
			qty = int(cart.get(str(product.id), 0))
			if qty <= 0:
				continue
			line_total = product.price * qty
			total += line_total
			addons = cart_addons.get(str(product.id), "")
			items.append({
				"product": product,
				"quantity": qty,
				"line_total": line_total,
				"addons": addons,
			})

		context = {
			"items": items,
			"total": total,
			"pickup_address": "Brgy. Parag-um, Carigara, Leyte.",
		}
		return render(request, "checkout.html", context)

	# POST: place order (pickup only)
	payment_method = (request.POST.get("payment_method") or "cash").strip().lower()

	# Validate stock before creating the order
	for product in products:
		qty = int(cart.get(str(product.id), 0))
		if qty <= 0:
			continue
		available = product.stock or 0
		if available < qty:
			messages.error(
				request,
				f"Not enough stock for {product.name}. Available: {available}, in your cart: {qty}.",
			)
			return redirect("customer_cart")

	order = Order.objects.create(customer=request.user)
	total = Decimal("0")
	for product in products:
		qty = int(cart.get(str(product.id), 0))
		if qty <= 0:
			continue
		line_total = product.price * qty
		total += line_total
		addons = cart_addons.get(str(product.id), "")
		order.items.create(product=product, quantity=qty, unit_price=product.price, addons=addons)

		# Decrease stock now that the order has been placed
		if product.stock is not None:
			new_stock = (product.stock or 0) - qty
			if new_stock < 0:
				new_stock = 0
			product.stock = new_stock
			product.save(update_fields=["stock"])

	order.total_amount = total
	order.save()
	request.session["cart"] = {}
	request.session["cart_addons"] = {}

	where = "for pickup"

	messages.success(
		request,
		f"Order #{order.id} has been placed {where}. Payment method: {payment_method.title()}.",
	)
	return redirect("customer_my_orders")


@login_required
def customer_profile(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	if request.method == "POST":
		form = ProfileForm(request.POST, instance=request.user)
		if form.is_valid():
			form.save()
			messages.success(request, "Profile updated successfully.")
			return redirect("customer_profile")
	else:
		form = ProfileForm(instance=request.user)

	return render(request, "profile.html", {"form": form})


@login_required
def customer_my_orders(request):
	if request.user.is_staff:
		return redirect("admin_dashboard")

	active_statuses = [
		Order.STATUS_PENDING,
		Order.STATUS_PREPARING,
		Order.STATUS_READY_FOR_PICKUP,
	]
	past_statuses = [
		Order.STATUS_COMPLETED,
		Order.STATUS_CANCELLED,
	]

	active_orders = (
		Order.objects.filter(customer=request.user, status__in=active_statuses)
		.order_by("-created_at")
		.prefetch_related("items__product")
	)
	past_orders = (
		Order.objects.filter(customer=request.user, status__in=past_statuses)
		.order_by("-created_at")
		.prefetch_related("items__product")
	)

	return render(
		request,
		"my_orders.html",
		{
			"active_orders": active_orders,
			"past_orders": past_orders,
		},
	)


@login_required
def admin_products(request):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	query = request.GET.get("q", "").strip()
	active_category = request.GET.get("category", "").strip()
	products = Product.objects.all()
	if query:
		products = products.filter(name__icontains=query)
	if active_category:
		products = products.filter(category=active_category)
	products = products.order_by("-created_at")

	if request.method == "POST":
		form = ProductForm(request.POST, request.FILES)
		if form.is_valid():
			form.save()
			messages.success(request, "Product added successfully.")
			return redirect("admin_products")
	else:
		form = ProductForm()

	context = {
		"form": form,
		"products": products,
		"editing": False,
		"query": query,
		"active_category": active_category,
	}
	return render(request, "product.html", context)


@login_required
def admin_product_edit(request, pk: int):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	product = get_object_or_404(Product, pk=pk)

	if request.method == "POST":
		form = ProductForm(request.POST, request.FILES, instance=product)
		if form.is_valid():
			form.save()
			messages.success(request, "Product updated successfully.")
			return redirect("admin_products")
	else:
		form = ProductForm(instance=product)

	query = request.GET.get("q", "").strip()
	active_category = request.GET.get("category", "").strip()
	products = Product.objects.all()
	if query:
		products = products.filter(name__icontains=query)
	if active_category:
		products = products.filter(category=active_category)
	products = products.order_by("-created_at")

	context = {
		"form": form,
		"products": products,
		"editing": True,
		"editing_product": product,
		"query": query,
		"active_category": active_category,
	}
	return render(request, "product.html", context)


@login_required
def admin_product_delete(request, pk: int):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	product = get_object_or_404(Product, pk=pk)

	if request.method == "POST":
		product.delete()
		messages.success(request, "Product deleted successfully.")
		return redirect("admin_products")

	return render(request, "product_confirm_delete.html", {"product": product})


@login_required
def admin_customers(request):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	customers = (
		User.objects.filter(is_staff=False)
		.annotate(order_count=Count("orders"))
		.order_by("-date_joined")
	)

	return render(request, "customers.html", {"customers": customers})


@login_required
def admin_orders(request):
	if not request.user.is_staff:
		return redirect("customer_dashboard")

	if request.method == "POST":
		order_id = request.POST.get("order_id")
		new_status = (request.POST.get("status") or "").strip()

		allowed_statuses = {
			Order.STATUS_PENDING,
			Order.STATUS_PREPARING,
			Order.STATUS_READY_FOR_PICKUP,
			Order.STATUS_COMPLETED,
			Order.STATUS_CANCELLED,
		}

		if order_id and new_status in allowed_statuses:
			try:
				order = Order.objects.get(pk=order_id)
				order.status = new_status
				order.save()
				messages.success(request, f"Updated Order #{order.id} status.")
			except Order.DoesNotExist:
				messages.error(request, "Order not found.")
		else:
			messages.error(request, "Invalid status update.")

		return redirect("admin_orders")

	orders = (
		Order.objects.select_related("customer")
		.order_by("-created_at")
		.prefetch_related("items__product")
	)

	return render(request, "admin_orders.html", {"orders": orders})

from django.urls import path
from . import views

urlpatterns = [
	path('', views.home, name='home'),
	path('login/', views.login_view, name='login'),
	path('logout/', views.logout_view, name='logout'),
	path('register/', views.register_view, name='register'),
	path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
	path('admin/products/', views.admin_products, name='admin_products'),
	path('admin/products/<int:pk>/', views.admin_product_edit, name='admin_product_edit'),
	path('admin/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
	path('admin/orders/', views.admin_orders, name='admin_orders'),
	path('admin/customers/', views.admin_customers, name='admin_customers'),
	path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
	path('customer/order-now/', views.customer_order_now, name='customer_order_now'),
	path('customer/products/<int:product_id>/', views.customer_product_detail, name='customer_product_detail'),
	path('customer/my-orders/', views.customer_my_orders, name='customer_my_orders'),
	path('customer/cart/', views.customer_cart_view, name='customer_cart'),
	path('customer/cart/update/<int:product_id>/', views.customer_cart_update, name='customer_cart_update'),
	path('customer/cart/add/<int:product_id>/', views.customer_cart_add, name='customer_cart_add'),
	path('customer/checkout/', views.customer_checkout, name='customer_checkout'),
	path('customer/profile/', views.customer_profile, name='customer_profile'),
]

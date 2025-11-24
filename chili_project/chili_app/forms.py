from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Product


class CustomerRegistrationForm(UserCreationForm):
	email = forms.EmailField(required=True)

	class Meta:
		model = User
		fields = ("username", "email", "password1", "password2")

	def save(self, commit=True):
		user = super().save(commit=False)
		user.email = self.cleaned_data["email"]
		user.is_staff = False
		if commit:
			user.save()
		return user


class ProductForm(forms.ModelForm):
	class Meta:
		model = Product
		fields = ["name", "category", "price", "stock", "is_active", "image"]


class ProfileForm(forms.ModelForm):
	class Meta:
		model = User
		fields = ["email"]

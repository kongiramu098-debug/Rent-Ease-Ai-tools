from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=[("customer", "Customer"), ("owner", "Shop owner")])

    class Meta:
        model = User
        fields = ("username", "email", "phone", "role")

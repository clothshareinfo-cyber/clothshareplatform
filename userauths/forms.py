from django import forms
from django.contrib.auth.forms import UserCreationForm
from userauths.models import User   # ✅ custom user model

class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username", "class": "form-input"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Email Address", "class": "form-input"})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Enter Password", "class": "form-input"})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password", "class": "form-input"})
    )

    class Meta:
        model = User   # ✅ your custom user model
        fields = ["username", "email", "password1", "password2"]


    
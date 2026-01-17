from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Почта")
    phone = forms.CharField(required=True, label="Телефон")

    class Meta:
        model = User
        fields = ("username", "email", "phone", "password1", "password2")

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        # простая нормализация
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        if len(phone) < 10:
            raise forms.ValidationError("Введите корректный номер телефона")

        return phone

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже существует")
        return email

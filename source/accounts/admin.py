from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("CRM", {
            "fields": (
                "role",
                "phone",
                "whatsapp",
                "telegram",
                "company",
                "sphere",
                "tags_text",
            )
        }),
    )

    list_display = (
        "username",
        "first_name",
        "last_name",
        "phone",
        "company",
        "role",
        "is_staff",
    )

    search_fields = ("username", "first_name", "last_name", "phone", "company")

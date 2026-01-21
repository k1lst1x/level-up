from django.contrib import admin
from .models import Category, Service


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "base_price",
        "instagram_url",
        "unit",
        "allow_multiple",
        "is_active",
        "sort_order",
        "updated_at",
    )
    list_filter = ("is_active", "allow_multiple", "category")
    search_fields = ("name", "category__name")
    ordering = ("sort_order", "name")

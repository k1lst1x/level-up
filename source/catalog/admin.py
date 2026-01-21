from django.contrib import admin
from .models import Category, Service


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name_ru", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_kk", "name_en")
    ordering = ("sort_order", "name_ru")

    fieldsets = (
        ("Названия", {
            "fields": ("name_ru", "name_kk", "name_en")
        }),
        ("Описания", {
            "fields": ("description_ru", "description_kk", "description_en")
        }),
        ("Медиа и настройки", {
            "fields": ("image", "sort_order", "is_active")
        }),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name_ru",
        "category",
        "base_price",
        "unit",
        "allow_multiple",
        "is_active",
        "sort_order",
        "updated_at",
    )
    list_filter = ("is_active", "allow_multiple", "category")
    search_fields = ("name_ru", "name_kk", "name_en", "category__name_ru")
    ordering = ("sort_order", "name_ru")

    fieldsets = (
        ("Категория", {
            "fields": ("category",)
        }),
        ("Названия", {
            "fields": ("name_ru", "name_kk", "name_en")
        }),
        ("Описания", {
            "fields": ("description_ru", "description_kk", "description_en")
        }),
        ("Параметры услуги", {
            "fields": ("base_price", "unit", "allow_multiple", "instagram_url")
        }),
        ("Медиа и статус", {
            "fields": ("image", "sort_order", "is_active")
        }),
    )

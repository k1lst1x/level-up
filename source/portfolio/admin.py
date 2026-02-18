# portfolio/admin.py
from django.contrib import admin
from .models import PortfolioCategory, PortfolioCase, PortfolioCasePhoto


@admin.register(PortfolioCategory)
class PortfolioCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name_ru", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_kk", "name_en")
    ordering = ("sort_order", "name_ru")


class PortfolioCasePhotoInline(admin.TabularInline):
    model = PortfolioCasePhoto
    extra = 3
    fields = ("image", "sort_order")


@admin.register(PortfolioCase)
class PortfolioCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title_ru", "category", "is_active", "sort_order", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("title_ru", "title_kk", "title_en")
    ordering = ("sort_order", "-created_at")
    inlines = [PortfolioCasePhotoInline]

    fieldsets = (
        ("Категория", {
            "fields": ("category",)
        }),
        ("Заголовки", {
            "fields": ("title_ru", "title_kk", "title_en")
        }),
        ("Описания", {
            "fields": ("description_ru", "description_kk", "description_en")
        }),
        ("Обложка и настройки", {
            "fields": ("cover", "sort_order", "is_active")
        }),
    )

# crm/admin.py
from django.contrib import admin
from .models import Contact, Deal, DealHistory


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "name",
        "phone",
        "whatsapp",
        "email",
        "telegram",
        "company",
        "sphere",
        "updated_at",
    )
    list_filter = ("owner",)
    search_fields = ("name", "phone", "whatsapp", "email", "telegram", "company", "sphere", "tags_text")
    ordering = ("-updated_at",)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "client", "name", "status", "amount", "updated_at")
    list_filter = ("status", "owner")
    search_fields = ("name", "client__name", "client__company", "notes")
    ordering = ("-updated_at",)


@admin.register(DealHistory)
class DealHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "deal", "changed_by", "from_status", "to_status", "created_at")
    list_filter = ("to_status", "from_status")
    search_fields = ("deal__name", "comment")
    ordering = ("created_at",)

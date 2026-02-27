# kp/admin.py
from django.contrib import admin

from .models import EventType, KPTemplate, Proposal, ProposalItem


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(KPTemplate)
class KPTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "event_type", "updated_at")
    search_fields = ("name",)
    list_filter = ("event_type", "show_cover", "show_intro", "show_gift", "show_footer")
    autocomplete_fields = ("event_type",)


class ProposalItemInline(admin.TabularInline):
    model = ProposalItem
    extra = 0
    autocomplete_fields = ("service",)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "owner", "customer", "updated_at")
    list_filter = ("status",)
    search_fields = ("id", "title", "owner__username", "customer__username")
    autocomplete_fields = ("owner", "customer", "template")
    inlines = [ProposalItemInline]


@admin.register(ProposalItem)
class ProposalItemAdmin(admin.ModelAdmin):
    list_display = ("id", "proposal", "service", "qty", "price", "discount")
    search_fields = ("proposal__id", "service__name")
    autocomplete_fields = ("proposal", "service")

# catalog/models.py
from __future__ import annotations

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Service(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="services")

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="services/", blank=True, null=True)

    base_price = models.IntegerField(blank=True, null=True)
    unit = models.CharField(max_length=64, blank=True, default="")

    # Если False — в КП нельзя увеличить qty выше 1 (одноразовая услуга)
    allow_multiple = models.BooleanField(
        default=True,
        verbose_name="Повторяемая (можно несколько раз)",
        help_text="Если выключено — услугу можно добавить в КП только один раз (qty всегда = 1).",
    )

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

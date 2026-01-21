# catalog/models.py
from __future__ import annotations

from django.db import models
from django.utils.translation import get_language


class Category(models.Model):
    name_ru = models.CharField("Название (RU)", max_length=255)
    name_kk = models.CharField("Название (KZ)", max_length=255, blank=True, default="")
    name_en = models.CharField("Название (EN)", max_length=255, blank=True, default="")

    description_ru = models.TextField("Описание (RU)", blank=True, default="")
    description_kk = models.TextField("Описание (KZ)", blank=True, default="")
    description_en = models.TextField("Описание (EN)", blank=True, default="")

    image = models.ImageField(upload_to="categories/", blank=True, null=True)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name_ru

    # 👉 универсальные свойства
    @property
    def name(self):
        lang = get_language()
        if lang == "kk" and self.name_kk:
            return self.name_kk
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru

    @property
    def description(self):
        lang = get_language()
        if lang == "kk" and self.description_kk:
            return self.description_kk
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description_ru


class Service(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="services")

    name_ru = models.CharField("Название (RU)", max_length=255)
    name_kk = models.CharField("Название (KZ)", max_length=255, blank=True, default="")
    name_en = models.CharField("Название (EN)", max_length=255, blank=True, default="")

    description_ru = models.TextField("Описание (RU)", blank=True, default="")
    description_kk = models.TextField("Описание (KZ)", blank=True, default="")
    description_en = models.TextField("Описание (EN)", blank=True, default="")

    image = models.ImageField(upload_to="services/", blank=True, null=True)

    base_price = models.IntegerField(blank=True, null=True)
    unit = models.CharField(max_length=64, blank=True, default="")

    instagram_url = models.URLField(blank=True, default="")

    allow_multiple = models.BooleanField(default=True)

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name_ru

    @property
    def name(self):
        lang = get_language()
        if lang == "kk" and self.name_kk:
            return self.name_kk
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru

    @property
    def description(self):
        lang = get_language()
        if lang == "kk" and self.description_kk:
            return self.description_kk
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description_ru

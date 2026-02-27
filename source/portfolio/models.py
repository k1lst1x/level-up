# portfolio/models.py
from __future__ import annotations

from django.db import models
from django.utils.translation import get_language


class PortfolioCategory(models.Model):
    name_ru = models.CharField("Название (RU)", max_length=255)
    name_kk = models.CharField("Название (KZ)", max_length=255, blank=True, default="")
    name_en = models.CharField("Название (EN)", max_length=255, blank=True, default="")
    sort_order = models.IntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

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


class PortfolioCase(models.Model):
    category = models.ForeignKey(
        PortfolioCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        verbose_name="Категория",
    )

    title_ru = models.CharField("Заголовок (RU)", max_length=255)
    title_kk = models.CharField("Заголовок (KZ)", max_length=255, blank=True, default="")
    title_en = models.CharField("Заголовок (EN)", max_length=255, blank=True, default="")

    description_ru = models.TextField("Описание (RU)", blank=True, default="")
    description_kk = models.TextField("Описание (KZ)", blank=True, default="")
    description_en = models.TextField("Описание (EN)", blank=True, default="")

    cover = models.ImageField("Обложка", upload_to="portfolio/covers/", blank=True, null=True)

    sort_order = models.IntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "Кейс"
        verbose_name_plural = "Кейсы"

    def __str__(self):
        return self.title_ru

    @property
    def title(self):
        lang = get_language()
        if lang == "kk" and self.title_kk:
            return self.title_kk
        if lang == "en" and self.title_en:
            return self.title_en
        return self.title_ru

    @property
    def description(self):
        lang = get_language()
        if lang == "kk" and self.description_kk:
            return self.description_kk
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description_ru


class PortfolioCasePhoto(models.Model):
    case = models.ForeignKey(
        PortfolioCase,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Кейс",
    )
    image = models.ImageField("Фото", upload_to="portfolio/photos/")
    sort_order = models.IntegerField("Порядок", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Фото"
        verbose_name_plural = "Фото"

    def __str__(self):
        return f"Фото #{self.pk} — {self.case.title_ru}"

# crm/models.py
from django.conf import settings
from django.db import models




User = settings.AUTH_USER_MODEL


class Contact(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="crm_contacts",
    )

    # базовое
    name = models.CharField(max_length=160)
    company = models.CharField(max_length=160, blank=True)
    sphere = models.CharField(max_length=160, blank=True)

    # контакты (phone обязателен, остальное нет)
    phone = models.CharField(max_length=32, help_text="Телефон клиента (обязательно)")
    whatsapp = models.CharField(max_length=32, blank=True, help_text="WhatsApp номер (необязательно)")
    email = models.EmailField(blank=True)
    telegram = models.CharField(max_length=64, blank=True, help_text="@username или ссылка t.me/...")

    tags_text = models.CharField(
        max_length=240,
        blank=True,
        help_text="Теги через запятую",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self):
        return self.name


class Deal(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        SENT = "SENT", "Отправлено"
        CONFIRMED = "CONFIRMED", "Подтверждено"
        REJECTED = "REJECTED", "Отказ"
        POSTPONED = "POSTPONED", "Отложено"

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="crm_deals",
    )

    client = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    name = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """
        FIX: поддерживаем сохранение вида instance.save(changed_by=user)
        и пишем историю смены статуса.
        """
        changed_by = kwargs.pop("changed_by", None)

        # Чтобы понять, менялся ли статус, берём старое значение из БД
        old_status = None
        if self.pk:
            old_status = Deal.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        super().save(*args, **kwargs)

        # Историю пишем только если статус реально поменялся
        if old_status is not None and old_status != self.status:
            DealHistory.objects.create(
                deal=self,
                changed_by=changed_by if changed_by is not None else self.owner,
                from_status=old_status,
                to_status=self.status,
                comment="",
            )


class DealHistory(models.Model):
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="history",
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="deal_changes",
    )

    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)

    comment = models.CharField(max_length=240, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.deal_id}: {self.from_status} → {self.to_status}"

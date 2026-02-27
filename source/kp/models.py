# kp/models.py
import secrets

from django.conf import settings
from django.db import models

from catalog.models import Service


class EventType(models.Model):
    """
    Тип мероприятия: Свадьба/Корпоратив/ДР и т.д.
    """
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class KPTemplate(models.Model):
    """
    Шаблон КП: какие блоки показывать, тексты, визуал.
    """
    name = models.CharField(max_length=160)
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT, related_name="templates")

    # Видимость блоков (услуги всегда показываются)
    show_cover = models.BooleanField(default=True)
    show_intro = models.BooleanField(default=True)
    show_gift = models.BooleanField(default=True)
    show_footer = models.BooleanField(default=True)

    # Вводный текст
    intro_title = models.CharField(max_length=160, blank=True, default="О наших услугах")
    intro_subtitle = models.TextField(blank=True, default="")

    # Подарок
    gift_text = models.CharField(
        max_length=220,
        blank=True,
        default="{client_name}, заберите ваш индивидуальный подарок!",
    )
    gift_button_text = models.CharField(max_length=80, blank=True, default="Забрать подарок")
    gift_button_url = models.URLField(blank=True, default="")

    # Подвал
    footer_text = models.TextField(
        blank=True,
        default="Спасибо за доверие. По вопросам — свяжитесь с нами в WhatsApp",
    )
    footer_copyright = models.CharField(max_length=120, blank=True, default="")

    # Визуальные настройки
    primary_color = models.CharField(max_length=16, blank=True, default="#6D28D9")
    secondary_color = models.CharField(max_length=16, blank=True, default="#1E3A8A")
    font_family = models.CharField(max_length=80, blank=True, default="Inter")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("event_type", "name")]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name

    def to_snapshot(self) -> dict:
        """
        Снимок шаблона, чтобы старые КП не ломались, если админ поменяет шаблон.
        """
        return {
            "name": self.name,
            "event_type_id": self.event_type_id,
            "blocksVisibility": {
                "cover": self.show_cover,
                "intro": self.show_intro,
                "gift": self.show_gift,
                "footer": self.show_footer,
                "services": True,
            },
            "intro": {"title": self.intro_title, "subtitle": self.intro_subtitle},
            "gift": {
                "text": self.gift_text,
                "buttonText": self.gift_button_text,
                "buttonUrl": self.gift_button_url,
            },
            "footer": {"text": self.footer_text, "copyright": self.footer_copyright},
            "visual": {
                "primaryColor": self.primary_color,
                "secondaryColor": self.secondary_color,
                "fontFamily": self.font_family,
            },
        }


class Proposal(models.Model):
    """
    Конкретное КП для конкретного заказчика.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        REQUESTED = "REQUESTED", "Запрос (клиент → менеджеру)"
        SENT = "SENT", "Отправлено/архив"
        CONFIRMED = "CONFIRMED", "Подтверждено"
        REJECTED = "REJECTED", "Отклонено"
        POSTPONED = "POSTPONED", "Перенесено"

    # Кто создал (менеджер/админ)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_proposals",
    )

    # Кто заказчик (кто открывает КП и выбирает услуги)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proposals",
    )

    template = models.ForeignKey(KPTemplate, on_delete=models.PROTECT, related_name="proposals")

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, default="")

    # Контекст мероприятия
    event_title = models.CharField(max_length=200, blank=True, default="")
    event_datetime = models.DateTimeField(null=True, blank=True)
    event_location = models.CharField(max_length=240, blank=True, default="")
    event_description = models.TextField(blank=True, default="")
    drive_link = models.URLField(blank=True, default="")

    # фото/обложка КП
    photo = models.ImageField(upload_to="kp/photos/", blank=True, null=True)

    # Снимок шаблона
    template_snapshot = models.JSONField(null=True, blank=True)

    # Публичная ссылка (если надо открыть без логина)
    public_token = models.CharField(max_length=64, blank=True, default="", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    fixed_subtotal = models.IntegerField(null=True, blank=True)
    fixed_extra = models.IntegerField(null=True, blank=True)
    fixed_total = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["customer", "status", "-updated_at"]),
            models.Index(fields=["public_token"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.customer.username})"

    def ensure_public_token(self):
        if not self.public_token:
            self.public_token = secrets.token_urlsafe(32)

    def ensure_template_snapshot(self):
        if self.template_snapshot is None:
            self.template_snapshot = self.template.to_snapshot()

    def save(self, *args, **kwargs):
        self.ensure_public_token()
        self.ensure_template_snapshot()
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())


class ProposalItem(models.Model):
    """
    Позиция КП: какая услуга, сколько, по какой цене.
    """
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    qty = models.PositiveIntegerField(default=1)

    # фиксируем цену на момент добавления в КП
    price = models.DecimalField(max_digits=12, decimal_places=2)

    # опционально
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    comment = models.CharField(max_length=240, blank=True, default="")

    class Meta:
        unique_together = [("proposal", "service")]
        indexes = [
            models.Index(fields=["proposal"]),
            models.Index(fields=["service"]),
        ]

    def __str__(self) -> str:
        return f"{self.service.name} x{self.qty}"

    @property
    def total_price(self):
        unit_price = self.price - self.discount
        if unit_price < 0:
            unit_price = 0
        return self.qty * unit_price

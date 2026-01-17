# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    # ===== CRM FIELDS =====
    phone = models.CharField("Телефон", max_length=32, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=32, blank=True)
    telegram = models.CharField("Telegram", max_length=64, blank=True)
    company = models.CharField("Компания", max_length=255, blank=True)
    sphere = models.CharField("Сфера", max_length=255, blank=True)
    tags_text = models.CharField("Теги", max_length=255, blank=True)

    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    def is_customer(self) -> bool:
        return self.role == self.Role.CUSTOMER

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.phone})"

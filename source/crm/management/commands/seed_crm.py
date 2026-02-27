# crm/management/commands/seed_crm.py
from __future__ import annotations

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from crm.models import Contact, Deal


User = get_user_model()


class Command(BaseCommand):
    help = "Seed CRM: contacts + deals for admin owner."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--contacts", type=int, default=40)
        parser.add_argument("--deals", type=int, default=60)
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR("crm: no superuser. Run seed_accounts first."))
            return

        if opts["clear"]:
            Deal.objects.all().delete()
            Contact.objects.all().delete()
            self.stdout.write(self.style.WARNING("crm: cleared"))

        contacts_n = int(opts["contacts"])
        deals_n = int(opts["deals"])

        contacts = []
        for i in range(contacts_n):
            name = f"Контакт {i+1}"
            c, _ = Contact.objects.get_or_create(
                owner=admin,
                name=name,
                defaults={
                    "contact": f"+7 777 {rnd.randrange(100,999)} {rnd.randrange(10,99)} {rnd.randrange(10,99)}",
                    "company": f"Компания {rnd.randrange(1, 20)}",
                    "sphere": rnd.choice(["Event", "Wedding", "Corporate", "PR", "Retail", "IT"]),
                    "budget": Decimal(rnd.randrange(100000, 5000000, 50000)),
                    "tags_text": rnd.choice(["vip, warm", "cold", "repeat", "urgent", ""]),
                },
            )
            contacts.append(c)

        statuses = [s[0] for s in Deal.Status.choices]  # DRAFT/SENT/...
        for j in range(deals_n):
            client = rnd.choice(contacts)
            Deal.objects.create(
                owner=admin,
                client=client,
                name=f"Сделка #{j+1} для {client.name}",
                amount=Decimal(rnd.randrange(200000, 15000000, 100000)),
                status=rnd.choice(statuses),
                notes="Сгенерировано сидером для демо.",
            )

        self.stdout.write(self.style.SUCCESS(f"crm: done. contacts={contacts_n}, deals={deals_n}"))

from __future__ import annotations

import random
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from crm.models import Contact, Deal, DealHistory


User = get_user_model()


class Command(BaseCommand):
    help = "Seed CRM: contacts, deals and status history for admin owner."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--contacts", type=int, default=40)
        parser.add_argument("--deals", type=int, default=60)
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            DealHistory.objects.all().delete()
            Deal.objects.all().delete()
            Contact.objects.all().delete()
            self.stdout.write(self.style.WARNING("crm: cleared"))

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.filter(is_staff=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR("crm: no admin user. Run seed_accounts first."))
            return

        contacts_n = int(opts["contacts"])
        deals_n = int(opts["deals"])

        spheres = [
            "Event",
            "Wedding",
            "Corporate",
            "Marketing",
            "Retail",
            "IT",
            "HoReCa",
            "Education",
            "FinTech",
        ]
        tag_sets = [
            "vip,warm",
            "cold",
            "repeat",
            "urgent",
            "new",
            "partner",
            "",
        ]

        contacts = []
        created_contacts = 0
        for i in range(contacts_n):
            name = f"Контакт {i+1}"
            c, created = Contact.objects.get_or_create(
                owner=admin,
                name=name,
                defaults={
                    "phone": f"+7 7{rnd.randrange(10,99)} {rnd.randrange(100,999)} {rnd.randrange(10,99)} {rnd.randrange(10,99)}",
                    "whatsapp": f"+7 7{rnd.randrange(10,99)} {rnd.randrange(100,999)} {rnd.randrange(10,99)} {rnd.randrange(10,99)}",
                    "email": f"contact{i+1}@example.com",
                    "telegram": f"@contact_{i+1}",
                    "company": f"Компания {rnd.randrange(1, 20)}",
                    "sphere": rnd.choice(spheres),
                    "tags_text": rnd.choice(tag_sets),
                },
            )

            if created:
                created_contacts += 1
            else:
                updates: list[str] = []
                if not c.phone:
                    c.phone = f"+7 7{rnd.randrange(10,99)} {rnd.randrange(100,999)} {rnd.randrange(10,99)} {rnd.randrange(10,99)}"
                    updates.append("phone")
                if not c.whatsapp:
                    c.whatsapp = c.phone
                    updates.append("whatsapp")
                if not c.email:
                    c.email = f"contact{i+1}@example.com"
                    updates.append("email")
                if not c.telegram:
                    c.telegram = f"@contact_{i+1}"
                    updates.append("telegram")
                if not c.company:
                    c.company = f"Компания {rnd.randrange(1, 20)}"
                    updates.append("company")
                if not c.sphere:
                    c.sphere = rnd.choice(spheres)
                    updates.append("sphere")
                if updates:
                    c.save(update_fields=updates)

            contacts.append(c)

        statuses = [s[0] for s in Deal.Status.choices]  # DRAFT/SENT/...
        created_deals = 0
        changed_status = 0
        for j in range(deals_n):
            client = rnd.choice(contacts)
            deal = Deal.objects.create(
                owner=admin,
                client=client,
                name=f"Сделка #{j+1} для {client.name}",
                amount=Decimal(rnd.randrange(200000, 15000000, 100000)),
                status=rnd.choice(statuses),
                notes="Сгенерировано сидером для демо.",
            )
            created_deals += 1

            # Часть сделок переводим в другой статус, чтобы появилась история изменений.
            if rnd.random() < 0.4:
                next_statuses = [x for x in statuses if x != deal.status]
                deal.status = rnd.choice(next_statuses)
                deal.save(update_fields=["status"], changed_by=admin)
                changed_status += 1

        self.stdout.write(
            self.style.SUCCESS(
                "crm: done. "
                f"contacts requested={contacts_n}, created={created_contacts}, total={Contact.objects.count()}; "
                f"deals created={created_deals}, with_history={changed_status}, total={Deal.objects.count()}"
            )
        )

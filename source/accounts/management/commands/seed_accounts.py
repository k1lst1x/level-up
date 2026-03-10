# accounts/management/commands/seed_accounts.py
from __future__ import annotations

import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Seed users: 1 admin + N customers (role-based), sets is_staff for admin."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--customers", type=int, default=25)
        parser.add_argument("--admin-username", type=str, default="admin")
        parser.add_argument("--admin-password", type=str, default="admin12345")
        parser.add_argument("--customer-password", type=str, default="customer12345")
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            # Чистим связанные сущности с PROTECT-ссылками на User.
            try:
                from kp.models import ProposalItem, Proposal, KPTemplate, EventType

                ProposalItem.objects.all().delete()
                Proposal.objects.all().delete()
                KPTemplate.objects.all().delete()
                EventType.objects.all().delete()
            except Exception:
                pass
            try:
                from crm.models import DealHistory, Deal, Contact

                DealHistory.objects.all().delete()
                Deal.objects.all().delete()
                Contact.objects.all().delete()
            except Exception:
                pass
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING("accounts: cleared users"))

        admin_username = opts["admin_username"]
        admin_password = opts["admin_password"]
        customer_password = opts["customer_password"]

        admin, created = User.objects.get_or_create(username=admin_username)
        admin.set_password(admin_password)

        # твоя модель юзера с role (ADMIN/CUSTOMER)
        if hasattr(admin, "role"):
            admin.role = getattr(admin, "Role").ADMIN  # type: ignore[attr-defined]
        admin.is_staff = True
        admin.is_superuser = True
        admin.phone = "+7 707 582 23 57"
        admin.whatsapp = "+7 707 582 23 57"
        admin.telegram = "@levelup_admin"
        admin.company = "Level-Up"
        admin.sphere = "Event Agency"
        admin.tags_text = "admin,vip"
        admin.email = "admin@example.com"
        admin.first_name = "Admin"
        admin.last_name = "User"
        admin.save()

        companies = [
            "Alem Events",
            "Qazaq Media",
            "Nomad Fest",
            "Skyline Group",
            "Prime Wedding",
            "Nova Retail",
            "Digital Orbit",
            "Aurora Labs",
            "White Hall",
            "Family Club",
        ]
        spheres = [
            "Wedding",
            "Corporate",
            "Retail",
            "IT",
            "PR",
            "Education",
            "HoReCa",
            "Private",
        ]
        tags = [
            "vip,warm",
            "new",
            "repeat",
            "cold",
            "urgent",
            "",
        ]

        created_customers = 0
        total_customers = int(opts["customers"])

        for i in range(total_customers):
            uname = f"customer{i+1}"
            u, c = User.objects.get_or_create(username=uname)
            if c:
                u.set_password(customer_password)
                created_customers += 1
            else:
                # Делаем пароль единым и предсказуемым для демо-логинов.
                u.set_password(customer_password)

            if hasattr(u, "role"):
                u.role = getattr(u, "Role").CUSTOMER  # type: ignore[attr-defined]
            u.is_staff = False
            u.is_superuser = False
            u.email = f"{uname}@example.com"
            u.first_name = f"Customer{i+1}"
            u.last_name = "Demo"
            u.phone = f"+7 7{rnd.randrange(10,99)} {rnd.randrange(100,999)} {rnd.randrange(10,99)} {rnd.randrange(10,99)}"
            u.whatsapp = u.phone
            u.telegram = f"@customer_{i+1}"
            u.company = companies[i % len(companies)]
            u.sphere = rnd.choice(spheres)
            u.tags_text = rnd.choice(tags)
            u.save()

        self.stdout.write(self.style.SUCCESS(
            "accounts: "
            f"admin={admin.username} (pass={admin_password}), "
            f"customers total={total_customers}, created={created_customers}, "
            f"customer_pass={customer_password}"
        ))

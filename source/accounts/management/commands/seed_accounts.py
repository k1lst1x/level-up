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
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING("accounts: cleared users"))

        admin_username = opts["admin_username"]
        admin_password = opts["admin_password"]

        admin, created = User.objects.get_or_create(username=admin_username)
        if created:
            admin.set_password(admin_password)

        # твоя модель юзера с role (ADMIN/CUSTOMER)
        if hasattr(admin, "role"):
            admin.role = getattr(admin, "Role").ADMIN  # type: ignore[attr-defined]
        admin.is_staff = True
        admin.is_superuser = True
        admin.email = "admin@example.com"
        admin.first_name = "Admin"
        admin.last_name = "User"
        admin.save()

        created_customers = 0
        total_customers = int(opts["customers"])

        for i in range(total_customers):
            uname = f"customer{i+1}"
            u, c = User.objects.get_or_create(username=uname)
            if c:
                u.set_password("customer12345")
                created_customers += 1

            if hasattr(u, "role"):
                u.role = getattr(u, "Role").CUSTOMER  # type: ignore[attr-defined]
            u.is_staff = False
            u.is_superuser = False
            u.email = f"{uname}@example.com"
            u.first_name = f"Customer{i+1}"
            u.last_name = "Demo"
            u.save()

        self.stdout.write(self.style.SUCCESS(
            f"accounts: admin={admin.username} (pass={admin_password}), customers total={total_customers}, created={created_customers}"
        ))

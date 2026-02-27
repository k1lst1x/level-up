from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Run all seeders: accounts, catalog, crm, kp."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear data before seeding where supported.")

    def handle(self, *args, **options):
        clear = options["clear"]

        self.stdout.write(self.style.WARNING("Seeding ALL..."))

        call_command("seed_accounts", clear=clear)

        call_command("seed_catalog", clear=clear)
        call_command("seed_crm", clear=clear)

        # kp может не существовать или модели могут отличаться
        try:
            call_command("seed_kp", clear=clear)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"seed_kp failed: {e}"))
            self.stdout.write(self.style.WARNING("KP seed skipped. Fix kp models/imports and rerun."))

        self.stdout.write(self.style.SUCCESS("Seed ALL done."))

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all seeders with dependency-safe clear and configurable volumes."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Hard clear all seeded entities before refill.")
        parser.add_argument("--seed", type=int, default=42)

        parser.add_argument("--admin-username", type=str, default="admin")
        parser.add_argument("--admin-password", type=str, default="admin12345")
        parser.add_argument("--customer-password", type=str, default="customer12345")
        parser.add_argument("--customers", type=int, default=80)

        parser.add_argument("--categories", type=int, default=10)
        parser.add_argument("--services-per-category", type=int, default=16)
        parser.add_argument("--contacts", type=int, default=120)
        parser.add_argument("--deals", type=int, default=240)

        parser.add_argument("--templates", type=int, default=8)
        parser.add_argument("--proposals", type=int, default=180)
        parser.add_argument("--items-min", type=int, default=3)
        parser.add_argument("--items-max", type=int, default=10)

        parser.add_argument("--portfolio-categories", type=int, default=6)
        parser.add_argument("--portfolio-cases", type=int, default=30)
        parser.add_argument("--portfolio-photos-min", type=int, default=4)
        parser.add_argument("--portfolio-photos-max", type=int, default=10)

        parser.add_argument("--with-images", action="store_true")
        parser.add_argument("--with-gallery", action="store_true")
        parser.add_argument("--with-links", action="store_true")
        parser.add_argument("--with-photos", action="store_true")

    def _hard_clear(self) -> None:
        from django.contrib.auth import get_user_model
        from catalog.models import Category, Service
        from crm.models import Contact, Deal, DealHistory
        from kp.models import EventType, KPTemplate, Proposal, ProposalItem
        from portfolio.models import PortfolioCase, PortfolioCasePhoto, PortfolioCategory

        ProposalItem.objects.all().delete()
        Proposal.objects.all().delete()
        KPTemplate.objects.all().delete()
        EventType.objects.all().delete()

        DealHistory.objects.all().delete()
        Deal.objects.all().delete()
        Contact.objects.all().delete()

        PortfolioCasePhoto.objects.all().delete()
        PortfolioCase.objects.all().delete()
        PortfolioCategory.objects.all().delete()

        Service.objects.all().delete()
        Category.objects.all().delete()

        User = get_user_model()
        User.objects.all().delete()

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding ALL..."))

        if options["clear"]:
            self._hard_clear()
            self.stdout.write(self.style.WARNING("seed_all: hard clear completed"))

        seed = int(options["seed"])

        call_command(
            "seed_accounts",
            seed=seed,
            customers=int(options["customers"]),
            admin_username=options["admin_username"],
            admin_password=options["admin_password"],
            customer_password=options["customer_password"],
            clear=False,
        )

        call_command(
            "seed_catalog",
            seed=seed,
            categories=int(options["categories"]),
            services_per_category=int(options["services_per_category"]),
            with_images=bool(options["with_images"]),
            with_gallery=bool(options["with_gallery"]),
            with_links=bool(options["with_links"]),
            clear=False,
        )

        call_command(
            "seed_crm",
            seed=seed,
            contacts=int(options["contacts"]),
            deals=int(options["deals"]),
            clear=False,
        )

        try:
            call_command(
                "seed_kp",
                seed=seed,
                templates=int(options["templates"]),
                proposals=int(options["proposals"]),
                items_min=int(options["items_min"]),
                items_max=int(options["items_max"]),
                with_photos=bool(options["with_photos"]),
                clear=False,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"seed_kp failed: {e}"))
            self.stdout.write(self.style.WARNING("KP seed skipped. Fix kp models/imports and rerun."))

        try:
            call_command(
                "seed_portfolio",
                seed=seed,
                categories=int(options["portfolio_categories"]),
                cases=int(options["portfolio_cases"]),
                photos_min=int(options["portfolio_photos_min"]),
                photos_max=int(options["portfolio_photos_max"]),
                with_images=bool(options["with_images"]),
                clear=False,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"seed_portfolio failed: {e}"))
            self.stdout.write(self.style.WARNING("Portfolio seed skipped."))

        self.stdout.write(self.style.SUCCESS("Seed ALL done."))

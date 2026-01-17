# catalog/management/commands/seed_catalog.py
from __future__ import annotations

import os
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from catalog.models import Category, Subcategory, Service


def _ensure_media_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _try_make_placeholder_image(rel_path: str, text: str) -> str | None:
    """
    Создаёт простую PNG в MEDIA_ROOT, если установлен Pillow.
    Возвращает rel_path, если получилось, иначе None.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        return None

    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return None

    abs_path = os.path.join(media_root, rel_path)
    _ensure_media_dir(abs_path)

    img = Image.new("RGB", (900, 650), (25, 25, 28))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([40, 40, 860, 610], radius=40, outline=(90, 90, 110), width=6)

    label = text[:28]
    draw.text((70, 80), label, fill=(240, 240, 245))
    draw.text((70, 130), "demo image", fill=(170, 170, 190))

    img.save(abs_path, format="PNG")
    return rel_path


class Command(BaseCommand):
    help = "Seed catalog: categories -> subcategories -> services (with optional placeholder images)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--categories", type=int, default=6)
        parser.add_argument("--subcategories", type=int, default=4)
        parser.add_argument("--services", type=int, default=12)
        parser.add_argument("--with-images", action="store_true")
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            Service.objects.all().delete()
            Subcategory.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("catalog: cleared"))

        cat_n = int(opts["categories"])
        sub_n = int(opts["subcategories"])
        svc_n = int(opts["services"])
        with_images = bool(opts["with_images"])

        category_names = [
            "Ведущие", "DJ", "Фотографы", "Видеографы", "Шоу-балет", "Фокусники",
            "Музыканты", "Декор", "Свет/Звук", "Пиротехника",
        ]
        sub_names = [
            "Премиум", "Стандарт", "Эконом", "ТОП", "Лайт", "PRO",
            "Свадьбы", "Корпоративы", "Дни рождения", "Открытия",
        ]

        created = {"cat": 0, "sub": 0, "svc": 0}

        for ci in range(cat_n):
            cname = category_names[ci % len(category_names)]
            cat, c = Category.objects.get_or_create(
                name=cname,
                defaults={
                    "description": f"Категория: {cname}",
                    "sort_order": ci,
                    "is_active": True,
                },
            )
            if c:
                created["cat"] += 1

            if with_images and not cat.image:
                rel = f"seed/categories/{cat.id}.png"
                made = _try_make_placeholder_image(rel, f"{cname}")
                if made:
                    cat.image = made
                    cat.save(update_fields=["image"])

            for si in range(sub_n):
                sname = sub_names[(ci * 3 + si) % len(sub_names)]
                sub, sc = Subcategory.objects.get_or_create(
                    category=cat,
                    name=sname,
                    defaults={
                        "description": f"{cname} / {sname}",
                        "sort_order": si,
                        "is_active": True,
                    },
                )
                if sc:
                    created["sub"] += 1

                if with_images and not sub.image:
                    rel = f"seed/subcategories/{sub.id}.png"
                    made = _try_make_placeholder_image(rel, f"{sname}")
                    if made:
                        sub.image = made
                        sub.save(update_fields=["image"])

                for k in range(svc_n):
                    price = Decimal(rnd.randrange(15000, 250000, 5000))
                    svc_name = f"{cname[:-1] if cname.endswith('ы') else cname} {sname} #{k+1}"
                    svc, scc = Service.objects.get_or_create(
                        subcategory=sub,
                        name=svc_name,
                        defaults={
                            "description": f"Описание {svc_name}. Коротко, чтобы было что читать.",
                            "base_price": price,
                            "unit": "шт",
                            "is_active": True,
                        },
                    )
                    if scc:
                        created["svc"] += 1

                    if with_images and not svc.image:
                        rel = f"seed/services/{svc.id}.png"
                        made = _try_make_placeholder_image(rel, svc_name)
                        if made:
                            svc.image = made
                            svc.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            f"catalog: done. created categories={created['cat']}, subcategories={created['sub']}, services={created['svc']}"
        ))

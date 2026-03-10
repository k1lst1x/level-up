from __future__ import annotations

import os
import random
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Category, Service


def _list_media_files(rel_dir: str) -> list[str]:
    media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "")
    if not media_root:
        return []

    base = media_root / rel_dir
    if not base.exists():
        return []

    items = [p for p in base.rglob("*") if p.is_file()]
    items.sort()
    return [str(p.relative_to(media_root)).replace("\\", "/") for p in items]


def _pick_by_index(items: list[str], index: int) -> str | None:
    if not items:
        return None
    return items[index % len(items)]


def _ensure_media_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _try_make_placeholder_image(rel_path: str, text: str) -> str | None:
    """
    Фолбэк, если нет готовых изображений в media/seed.
    """
    try:
        from PIL import Image, ImageDraw  # type: ignore
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
    draw.text((70, 80), text[:32], fill=(240, 240, 245))
    draw.text((70, 130), "catalog seed", fill=(170, 170, 190))
    img.save(abs_path, format="PNG")
    return rel_path


class Command(BaseCommand):
    help = "Seed catalog with localized categories/services and optional media."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--categories", type=int, default=8)
        parser.add_argument("--services-per-category", type=int, default=14)
        parser.add_argument("--services", type=int, default=None, help="Alias for --services-per-category")
        parser.add_argument("--with-images", action="store_true")
        parser.add_argument("--with-gallery", action="store_true")
        parser.add_argument("--with-links", action="store_true")
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            Service.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("catalog: cleared"))

        cat_n = int(opts["categories"])
        svc_n = int(opts["services"] if opts["services"] is not None else opts["services_per_category"])
        with_images = bool(opts["with_images"])
        with_gallery = bool(opts["with_gallery"])
        with_links = bool(opts["with_links"])

        category_images = _list_media_files("seed/categories")
        service_images = _list_media_files("seed/services")

        category_pool = [
            ("Ведущие", "Жүргізушілер", "Hosts"),
            ("DJ", "DJ", "DJ"),
            ("Фотографы", "Фотографтар", "Photographers"),
            ("Видеографы", "Видеографтар", "Videographers"),
            ("Шоу-программы", "Шоу бағдарламалар", "Show Programs"),
            ("Музыканты", "Музыканттар", "Musicians"),
            ("Декор", "Декор", "Decor"),
            ("Свет и звук", "Жарық және дыбыс", "Light and Sound"),
            ("Пиротехника", "Пиротехника", "Pyrotechnics"),
            ("Кейтеринг", "Кейтеринг", "Catering"),
            ("Технический персонал", "Техникалық команда", "Technical Crew"),
            ("Площадки", "Локациялар", "Venues"),
        ]
        service_tiers = [
            ("Базовый пакет", "Базалық пакет", "Basic Package"),
            ("Стандарт", "Стандарт", "Standard"),
            ("Премиум", "Премиум", "Premium"),
            ("VIP", "VIP", "VIP"),
            ("Лайт", "Жеңіл", "Lite"),
            ("PRO", "PRO", "PRO"),
            ("Под ключ", "Кілтпен", "Turnkey"),
            ("Вечерний", "Кешкі", "Evening"),
            ("Полный день", "Толық күн", "Full Day"),
            ("Авторский", "Авторлық", "Signature"),
        ]
        youtube_pool = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
            "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
            "https://www.youtube.com/watch?v=RgKAFK5djSk",
            "https://www.youtube.com/watch?v=ktvTqknDobU",
        ]
        insta_pool = [
            "https://www.instagram.com/p/C6zCwAsoN7R/",
            "https://www.instagram.com/p/C7P7m0Jt0vN/",
            "https://www.instagram.com/reel/C6nLzMct3pS/",
            "https://www.instagram.com/reel/C7YdS1gN6Y3/",
            "https://www.instagram.com/p/C8AcR2UNY2B/",
            "https://www.instagram.com/reel/C8jM5B3NEX5/",
        ]
        units = ["услуга", "час", "пакет", "смена"]

        created = {"cat": 0, "svc": 0}
        service_index = 0

        for ci in range(cat_n):
            ru, kk, en = category_pool[ci % len(category_pool)]
            cat, cat_created = Category.objects.get_or_create(
                name_ru=ru,
                defaults={
                    "name_kk": kk,
                    "name_en": en,
                    "description_ru": f"{ru}: услуги для мероприятий, корпоративов и частных событий.",
                    "description_kk": f"{kk}: іс-шараларға арналған қызметтер топтамасы.",
                    "description_en": f"{en}: services for events, private and corporate occasions.",
                    "sort_order": ci,
                    "is_active": True,
                },
            )
            if cat_created:
                created["cat"] += 1

            cat_updates: list[str] = []
            if not cat.name_kk:
                cat.name_kk = kk
                cat_updates.append("name_kk")
            if not cat.name_en:
                cat.name_en = en
                cat_updates.append("name_en")
            if not cat.description_ru:
                cat.description_ru = f"{ru}: услуги для мероприятий, корпоративов и частных событий."
                cat_updates.append("description_ru")
            if not cat.description_kk:
                cat.description_kk = f"{kk}: іс-шараларға арналған қызметтер топтамасы."
                cat_updates.append("description_kk")
            if not cat.description_en:
                cat.description_en = f"{en}: services for events, private and corporate occasions."
                cat_updates.append("description_en")
            if with_images and not cat.image:
                cat_image = _pick_by_index(category_images, ci)
                if not cat_image:
                    cat_image = _try_make_placeholder_image(f"seed/categories/{ci + 1}.png", ru)
                if cat_image:
                    cat.image = cat_image
                    cat_updates.append("image")
            if cat_updates:
                cat.save(update_fields=cat_updates)

            for si in range(svc_n):
                tr_ru, tr_kk, tr_en = service_tiers[si % len(service_tiers)]
                name_ru = f"{ru} {tr_ru} #{si + 1}"
                name_kk = f"{kk} {tr_kk} #{si + 1}"
                name_en = f"{en} {tr_en} #{si + 1}"

                base_price = rnd.randrange(30000, 900000, 5000)
                service, svc_created = Service.objects.get_or_create(
                    category=cat,
                    name_ru=name_ru,
                    defaults={
                        "name_kk": name_kk,
                        "name_en": name_en,
                        "description_ru": f"{name_ru}. Подходит для мероприятий среднего и высокого уровня.",
                        "description_kk": f"{name_kk}. Орта және премиум форматтағы іс-шараларға лайық.",
                        "description_en": f"{name_en}. Suitable for mid-level and premium events.",
                        "base_price": base_price,
                        "unit": rnd.choice(units),
                        "allow_multiple": rnd.random() > 0.15,
                        "sort_order": si,
                        "is_active": True,
                    },
                )
                if svc_created:
                    created["svc"] += 1

                svc_updates: list[str] = []
                if not service.name_kk:
                    service.name_kk = name_kk
                    svc_updates.append("name_kk")
                if not service.name_en:
                    service.name_en = name_en
                    svc_updates.append("name_en")
                if not service.description_ru:
                    service.description_ru = f"{name_ru}. Подходит для мероприятий среднего и высокого уровня."
                    svc_updates.append("description_ru")
                if not service.description_kk:
                    service.description_kk = f"{name_kk}. Орта және премиум форматтағы іс-шараларға лайық."
                    svc_updates.append("description_kk")
                if not service.description_en:
                    service.description_en = f"{name_en}. Suitable for mid-level and premium events."
                    svc_updates.append("description_en")
                if service.base_price in (None, 0):
                    service.base_price = base_price
                    svc_updates.append("base_price")
                if not service.unit:
                    service.unit = rnd.choice(units)
                    svc_updates.append("unit")

                if with_links and not service.youtube_url:
                    service.youtube_url = youtube_pool[(service_index + si) % len(youtube_pool)]
                    svc_updates.append("youtube_url")
                if with_links and not service.instagram_url:
                    service.instagram_url = insta_pool[(service_index + si) % len(insta_pool)]
                    svc_updates.append("instagram_url")
                if with_links and not service.instagram_urls:
                    links = rnd.sample(insta_pool, k=min(len(insta_pool), rnd.randint(2, 4)))
                    service.instagram_urls = "\n".join(links)
                    svc_updates.append("instagram_urls")

                if with_images and not service.image:
                    main_image = _pick_by_index(service_images, service_index)
                    if not main_image:
                        main_image = _try_make_placeholder_image(f"seed/services/{service_index + 1}.png", name_ru)
                    if main_image:
                        service.image = main_image
                        svc_updates.append("image")

                if with_images and with_gallery:
                    gallery_fields = ("image_2", "image_3", "image_4", "image_5", "image_6")
                    for offset, field_name in enumerate(gallery_fields, start=1):
                        if getattr(service, field_name):
                            continue
                        gallery_image = _pick_by_index(service_images, service_index + offset * 3)
                        if gallery_image:
                            setattr(service, field_name, gallery_image)
                            svc_updates.append(field_name)

                if svc_updates:
                    service.save(update_fields=svc_updates)

                service_index += 1

        self.stdout.write(
            self.style.SUCCESS(
                "catalog: done. "
                f"created categories={created['cat']}, services={created['svc']}; "
                f"total categories={Category.objects.count()}, services={Service.objects.count()}"
            )
        )

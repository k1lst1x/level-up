from __future__ import annotations

import os
import random
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from portfolio.models import PortfolioCase, PortfolioCasePhoto, PortfolioCategory


def _list_media_files(rel_dir: str) -> list[str]:
    media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "")
    if not media_root:
        return []
    base = media_root / rel_dir
    if not base.exists():
        return []
    files = [p for p in base.rglob("*") if p.is_file()]
    files.sort()
    return [str(p.relative_to(media_root)).replace("\\", "/") for p in files]


def _pick_by_index(items: list[str], index: int) -> str | None:
    if not items:
        return None
    return items[index % len(items)]


def _ensure_media_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _try_make_placeholder_image(rel_path: str, text: str) -> str | None:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        return None

    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return None

    abs_path = os.path.join(media_root, rel_path)
    _ensure_media_dir(abs_path)

    img = Image.new("RGB", (1200, 900), (22, 22, 28))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([60, 60, 1140, 840], radius=46, outline=(110, 110, 140), width=6)
    draw.text((100, 120), "PORTFOLIO CASE", fill=(242, 242, 250))
    draw.text((100, 190), text[:36], fill=(188, 188, 208))
    img.save(abs_path, format="PNG")
    return rel_path


class Command(BaseCommand):
    help = "Seed portfolio categories, cases and gallery photos."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--categories", type=int, default=6)
        parser.add_argument("--cases", type=int, default=24)
        parser.add_argument("--photos-min", type=int, default=3)
        parser.add_argument("--photos-max", type=int, default=8)
        parser.add_argument("--with-images", action="store_true")
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])

        if opts["clear"]:
            PortfolioCasePhoto.objects.all().delete()
            PortfolioCase.objects.all().delete()
            PortfolioCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING("portfolio: cleared"))

        categories_n = int(opts["categories"])
        cases_n = int(opts["cases"])
        photos_min = int(opts["photos_min"])
        photos_max = int(opts["photos_max"])
        with_images = bool(opts["with_images"])

        if photos_min > photos_max:
            photos_min, photos_max = photos_max, photos_min

        category_pool = [
            ("Свадьбы", "Үйлену тойлары", "Weddings"),
            ("Корпоративы", "Корпоративтер", "Corporate Events"),
            ("Private events", "Жеке іс-шаралар", "Private Events"),
            ("Концерты", "Концерттер", "Concerts"),
            ("Промо", "Промо", "Promotions"),
            ("Открытия", "Ашылулар", "Openings"),
            ("Фестивали", "Фестивальдер", "Festivals"),
            ("Выставки", "Көрмелер", "Exhibitions"),
        ]

        cover_pool = _list_media_files("portfolio/covers")
        photo_pool = _list_media_files("portfolio/photos")
        if not cover_pool:
            cover_pool = _list_media_files("seed/kp/photos")
        if not photo_pool:
            photo_pool = _list_media_files("seed/services")

        categories: list[PortfolioCategory] = []
        created_categories = 0
        for i in range(categories_n):
            ru, kk, en = category_pool[i % len(category_pool)]
            cat, created = PortfolioCategory.objects.get_or_create(
                name_ru=ru,
                defaults={
                    "name_kk": kk,
                    "name_en": en,
                    "sort_order": i,
                    "is_active": True,
                },
            )
            if created:
                created_categories += 1
            else:
                updates: list[str] = []
                if not cat.name_kk:
                    cat.name_kk = kk
                    updates.append("name_kk")
                if not cat.name_en:
                    cat.name_en = en
                    updates.append("name_en")
                if updates:
                    cat.save(update_fields=updates)
            categories.append(cat)

        if not categories:
            self.stdout.write(self.style.ERROR("portfolio: no categories generated"))
            return

        created_cases = 0
        created_photos = 0
        for idx in range(cases_n):
            category = rnd.choice(categories)
            title_ru = f"{category.name_ru}: кейс #{idx + 1}"
            title_kk = f"{category.name_kk or category.name_ru}: кейс #{idx + 1}"
            title_en = f"{category.name_en or category.name_ru}: case #{idx + 1}"

            case, created = PortfolioCase.objects.get_or_create(
                category=category,
                title_ru=title_ru,
                defaults={
                    "title_kk": title_kk,
                    "title_en": title_en,
                    "description_ru": "Организация мероприятия под ключ: концепция, команда, технический продакшн и сопровождение.",
                    "description_kk": "Іс-шараны толық ұйымдастыру: концепция, команда, техникалық продакшн және сүйемелдеу.",
                    "description_en": "End-to-end event production: concept, team, technical setup and live support.",
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            if created:
                created_cases += 1

            case_updates: list[str] = []
            if not case.title_kk:
                case.title_kk = title_kk
                case_updates.append("title_kk")
            if not case.title_en:
                case.title_en = title_en
                case_updates.append("title_en")
            if not case.description_ru:
                case.description_ru = "Организация мероприятия под ключ: концепция, команда, технический продакшн и сопровождение."
                case_updates.append("description_ru")
            if not case.description_kk:
                case.description_kk = "Іс-шараны толық ұйымдастыру: концепция, команда, техникалық продакшн және сүйемелдеу."
                case_updates.append("description_kk")
            if not case.description_en:
                case.description_en = "End-to-end event production: concept, team, technical setup and live support."
                case_updates.append("description_en")

            if with_images and not case.cover:
                cover = _pick_by_index(cover_pool, idx)
                if not cover:
                    cover = _try_make_placeholder_image(f"portfolio/covers/seed_case_{idx + 1}.png", case.title_ru)
                if cover:
                    case.cover = cover
                    case_updates.append("cover")

            if case_updates:
                case.save(update_fields=case_updates)

            target_photos = rnd.randint(photos_min, photos_max)
            current = case.photos.count()
            to_create = max(0, target_photos - current)

            for photo_idx in range(to_create):
                image = None
                if with_images:
                    image = _pick_by_index(photo_pool, idx * max(1, photos_max) + photo_idx)
                    if not image:
                        image = _try_make_placeholder_image(
                            f"portfolio/photos/seed_case_{idx + 1}_{photo_idx + 1}.png",
                            case.title_ru,
                        )
                if not image:
                    continue

                PortfolioCasePhoto.objects.create(
                    case=case,
                    image=image,
                    sort_order=current + photo_idx,
                )
                created_photos += 1

        self.stdout.write(
            self.style.SUCCESS(
                "portfolio: done. "
                f"created categories={created_categories}, cases={created_cases}, photos={created_photos}; "
                f"total categories={PortfolioCategory.objects.count()}, "
                f"cases={PortfolioCase.objects.count()}, photos={PortfolioCasePhoto.objects.count()}"
            )
        )

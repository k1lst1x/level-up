# main/views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.translation import get_language
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from catalog.models import Category, Service


def _is_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False

    # Django-истина ВСЕГДА главнее
    if user.is_superuser or user.is_staff:
        return True

    # кастомное is_admin — только как доп. сигнал
    try:
        attr = getattr(user, "is_admin", None)
        if callable(attr):
            return bool(attr())
        if isinstance(attr, bool):
            return bool(attr)
    except Exception:
        pass

    return False


def _normalize_words(text: str) -> list[str]:
    raw = text.lower().strip()
    parts = [p for p in raw.replace(",", " ").split() if len(p) > 1]

    bases: set[str] = set()

    for w in parts:
        bases.add(w)

        # агрессивнее режем окончания
        for i in (1, 2, 3):
            if len(w) - i >= 4:
                bases.add(w[:-i])

    return list(bases)


def _lang_suffix() -> str:
    lang = (get_language() or "ru").lower()
    if lang.startswith("kk"):
        return "kk"
    if lang.startswith("en"):
        return "en"
    return "ru"


def _category_search_q(search: str) -> Q:
    words = _normalize_words(search)

    q = Q()
    for w in words:
        q |= (
            Q(name_ru__icontains=w) |
            Q(name_kk__icontains=w) |
            Q(name_en__icontains=w) |
            Q(description_ru__icontains=w) |
            Q(description_kk__icontains=w) |
            Q(description_en__icontains=w) |
            Q(services__name_ru__icontains=w) |
            Q(services__name_kk__icontains=w) |
            Q(services__name_en__icontains=w) |
            Q(services__description_ru__icontains=w) |
            Q(services__description_kk__icontains=w) |
            Q(services__description_en__icontains=w)
        )

    return q


def _service_search_q(search: str) -> Q:
    words = _normalize_words(search)

    q = Q()
    for w in words:
        q |= (
            Q(name_ru__icontains=w) |
            Q(name_kk__icontains=w) |
            Q(name_en__icontains=w) |
            Q(description_ru__icontains=w) |
            Q(description_kk__icontains=w) |
            Q(description_en__icontains=w)
        )

    return q


def _search_q(search: str) -> Q:
    # универсальный поиск по услугам
    return (
        Q(name_ru__icontains=search) |
        Q(name_kk__icontains=search) |
        Q(name_en__icontains=search) |
        Q(description_ru__icontains=search) |
        Q(description_kk__icontains=search) |
        Q(description_en__icontains=search)
    )


def _order_by_if_exists(qs, *fields: str):
    model_fields = {f.name for f in qs.model._meta.get_fields()}
    safe = []

    suffix = _lang_suffix()

    for f in fields:
        raw = f[1:] if f.startswith("-") else f

        # если просим "name" -> заменяем на name_ru/name_en/name_kk
        if raw == "name":
            raw = f"name_{suffix}"
            if f.startswith("-"):
                raw = "-" + raw

        if raw.lstrip("-") in model_fields:
            safe.append(raw)

    if not safe:
        # дефолтная сортировка тоже должна быть корректной
        safe = [f"name_{suffix}"]

    return qs.order_by(*safe)


def home(request):
    is_admin = _is_admin(request.user)

    qs = Category.objects.all()
    if not is_admin:
        qs = qs.filter(is_active=True)

    search = (request.GET.get("search") or "").strip()

    if search:
        qs = qs.filter(_category_search_q(search)).distinct()

    categories = _order_by_if_exists(qs, "sort_order", "name")

    return render(
        request,
        "main/home.html",
        {
            "categories": categories,
            "search": search,
            "is_admin": is_admin,
        },
    )


@login_required
def categories_page(request):
    is_admin = _is_admin(request.user)

    qs = Category.objects.all()
    if not is_admin:
        qs = qs.filter(is_active=True)

    search = (request.GET.get("search") or "").strip()

    if search:
        qs = qs.filter(_category_search_q(search)).distinct()

    categories = _order_by_if_exists(qs, "sort_order", "name")

    return render(
        request,
        "main/categories.html",
        {
            "categories": categories,
            "search": search,
            "is_admin": is_admin,
        },
    )


@login_required
def category_services_page(request, category_id: int):
    is_admin = _is_admin(request.user)

    category_qs = Category.objects.all()
    if not is_admin:
        category_qs = category_qs.filter(is_active=True)

    category = get_object_or_404(category_qs, id=category_id)

    services_qs = Service.objects.filter(category=category)
    if not is_admin:
        services_qs = services_qs.filter(is_active=True)

    search = (request.GET.get("search") or "").strip()
    if search:
        services_qs = services_qs.filter(_search_q(search))

    services = _order_by_if_exists(services_qs, "sort_order", "name")

    draft_kps = []
    has_draft_kps = False

    if is_admin:
        from kp.models import Proposal

        # У тебя в базе статус именно "DRAFT" (ты сам это показал),
        # так что не выдумываем.
        draft_kps = (
            Proposal.objects
            .filter(owner=request.user, status="DRAFT")
            .select_related("customer", "owner")
            .order_by("-updated_at")
        )
        has_draft_kps = draft_kps.exists()

    return render(
        request,
        "main/category_services.html",
        {
            "category": category,
            "services": services,
            "search": search,
            "draft_kps": draft_kps,
            "has_draft_kps": has_draft_kps,
            "is_admin": is_admin,
        },
    )


@login_required
def crm_page(request):
    return render(request, "main/crm.html")


@login_required
def kp_page(request):
    return redirect(reverse("kp:kp"))

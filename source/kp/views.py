from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from accounts.permissions import IsCustomerRole
from catalog.models import Service
from .models import EventType, Proposal, ProposalItem, KPTemplate
from .serializers import ProposalSerializer

User = get_user_model()
ACTIVE_KP_SESSION_KEY = "active_kp_id"

AUTO_CLOSE_HOURS = 16  # автозакрытие после начала мероприятия


# =========================
# role helpers
# =========================
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


def _status(name: str, fallback: Optional[Any] = None):
    """
    Proposal.Status.* может быть Enum/TextChoices.
    Возвращаем статус, если есть, иначе fallback.
    """
    try:
        return getattr(Proposal.Status, name)
    except Exception:
        return fallback


STATUS_DRAFT = _status("DRAFT", "DRAFT")
STATUS_REQUESTED = _status("REQUESTED", "REQUESTED")
STATUS_SENT = _status("SENT", _status("SUBMITTED", _status("DONE", "SENT")))
STATUS_CONFIRMED = _status("CONFIRMED", "CONFIRMED")
STATUS_REJECTED = _status("REJECTED", "REJECTED")


# =========================
# DRF API (customer only)
# =========================
class CustomerProposalViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsCustomerRole]
    serializer_class = ProposalSerializer

    def get_queryset(self):
        return (
            Proposal.objects
            .filter(customer=self.request.user)
            .prefetch_related("items__service", "template")
        )


class AddServiceToProposalAPIView(views.APIView):
    permission_classes = [IsCustomerRole]

    def post(self, request, proposal_id: int):
        proposal = get_object_or_404(Proposal, id=proposal_id, customer=request.user)

        service_id = request.data.get("service_id")
        qty_raw = request.data.get("qty", 1)

        try:
            qty = int(qty_raw)
        except Exception:
            return Response({"detail": "qty должен быть числом"}, status=status.HTTP_400_BAD_REQUEST)

        if not service_id:
            return Response({"detail": "service_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        if qty <= 0:
            return Response({"detail": "qty должен быть > 0"}, status=status.HTTP_400_BAD_REQUEST)

        service = get_object_or_404(Service, id=service_id, is_active=True)

        item, created = ProposalItem.objects.get_or_create(
            proposal=proposal,
            service=service,
            defaults={"qty": qty, "price": service.base_price or 0},
        )
        if not created:
            item.qty = qty
            item.save(update_fields=["qty"])

        return Response({"detail": "ok"})


# =========================
# helpers
# =========================
def _pick_default_template() -> KPTemplate:
    """
    Берём самый свежий шаблон.
    Если шаблонов нет вообще — создаём базовый EventType и базовый KPTemplate.
    """
    tpl = KPTemplate.objects.filter(event_type__is_active=True).order_by("-updated_at").first()
    if tpl:
        return tpl

    tpl = KPTemplate.objects.order_by("-updated_at").first()
    if tpl:
        return tpl

    with transaction.atomic():
        tpl = KPTemplate.objects.select_for_update().order_by("-updated_at").first()
        if tpl:
            return tpl

        event_type = EventType.objects.filter(is_active=True).order_by("id").first()
        if not event_type:
            event_type = EventType.objects.create(name="Общее", is_active=True)

        tpl, _ = KPTemplate.objects.get_or_create(
            event_type=event_type,
            name="Базовый",
            defaults={
                "show_cover": True,
                "show_intro": True,
                "show_gift": True,
                "show_footer": True,
                "intro_title": "О наших услугах",
                "intro_subtitle": "",
                "gift_text": "{client_name}, заберите ваш индивидуальный подарок!",
                "gift_button_text": "Забрать подарок",
                "gift_button_url": "",
                "footer_text": "Спасибо за доверие. По вопросам — свяжитесь с нами в WhatsApp",
                "footer_copyright": "",
                "primary_color": "#6D28D9",
                "secondary_color": "#1E3A8A",
                "font_family": "Inter",
            },
        )
        return tpl


def _get_active_kp_for_admin(request) -> Optional[Proposal]:
    kp_id = request.session.get(ACTIVE_KP_SESSION_KEY)
    if not kp_id:
        return None
    return (
        Proposal.objects
        .filter(id=kp_id, owner=request.user, status=STATUS_DRAFT)
        .select_related("customer", "template")
        .first()
    )


def _set_active_kp(request, kp: Proposal) -> None:
    request.session[ACTIVE_KP_SESSION_KEY] = kp.id


def _clear_active_kp(request) -> None:
    request.session.pop(ACTIVE_KP_SESSION_KEY, None)


def _get_or_create_customer_draft(customer: User) -> Proposal:
    """
    CUSTOMER: один черновик как "корзина".
    """
    draft = (
        Proposal.objects
        .filter(customer=customer, owner=customer, status=STATUS_DRAFT)
        .order_by("-updated_at", "-id")
        .first()
    )
    if draft:
        return draft

    tpl = _pick_default_template()
    return Proposal.objects.create(
        owner=customer,
        customer=customer,
        template=tpl,
        title=f"КП для {customer.username}",
        status=STATUS_DRAFT,
    )


def _get_or_create_admin_draft(owner: User, customer: User, *, force_new: bool = False) -> Proposal:
    """
    ADMIN: один draft на пару (owner, customer), если force_new=False.
    """
    qs = (
        Proposal.objects
        .select_for_update()
        .filter(owner=owner, customer=customer, status=STATUS_DRAFT)
        .order_by("-updated_at", "-id")
    )

    if not force_new:
        existing = qs.first()
        if existing:
            return existing

    tpl = _pick_default_template()
    return Proposal.objects.create(
        owner=owner,
        customer=customer,
        template=tpl,
        title=f"КП для {customer.username}",
        status=STATUS_DRAFT,
    )


def _notes_json_load(kp: Optional[Proposal]) -> dict[str, Any]:
    if not kp:
        return {}
    raw = getattr(kp, "notes", "") or ""
    try:
        data = json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _notes_json_save(kp: Proposal, data: dict[str, Any]) -> None:
    kp.notes = json.dumps(data, ensure_ascii=False)


def _parse_dt_local(dt_raw: str):
    if not dt_raw:
        return None
    dt = parse_datetime(dt_raw)
    if dt:
        return dt
    try:
        return datetime.fromisoformat(dt_raw)
    except Exception:
        return None

from decimal import Decimal, ROUND_HALF_UP

def _calc_totals(items, *, add_percent: int = 20):
    """
    subtotal: сумма по строкам
    extra: надбавка add_percent%
    total: subtotal + extra
    Возвращаем int, чтобы без Decimal-ада в шаблоне.
    """
    subtotal = 0
    for it in items:
        try:
            subtotal += int(it.qty) * int(it.price or 0)
        except Exception:
            pass

    extra = int((Decimal(subtotal) * Decimal(add_percent) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total = subtotal + extra
    return subtotal, extra, total


def _calc_total_sum(items) -> int:
    total = 0
    for it in items:
        tp = getattr(it, "total_price", None)
        if tp is not None:
            try:
                total += int(tp)
                continue
            except Exception:
                pass
        try:
            total += int(it.qty) * int(it.price or 0)
        except Exception:
            pass
    return total

import json
from decimal import Decimal

@login_required
@require_POST
@transaction.atomic
def update_item_price(request, item_id: int):
    """
    Admin-only. Меняет ProposalItem.price и возвращает пересчитанные суммы.
    """
    if not _is_admin(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    item = get_object_or_404(ProposalItem.objects.select_related("proposal"), id=item_id)
    kp = item.proposal

    # админ может менять только свои КП и только в редактируемых статусах
    if kp.owner_id != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED):
        return JsonResponse({"ok": False, "error": "not editable"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    raw_price = payload.get("price")
    if raw_price is None:
        return JsonResponse({"ok": False, "error": "price required"}, status=400)

    # price только >= 0
    try:
        price_int = int(Decimal(str(raw_price)))
    except Exception:
        return JsonResponse({"ok": False, "error": "bad price"}, status=400)

    if price_int < 0:
        price_int = 0

    item.price = price_int
    item.save(update_fields=["price"])

    # пересчёт строки и итога
    items = list(kp.items.all())
    subtotal, extra20, total = _calc_totals(items, add_percent=20)

    item_total = 0
    try:
        item_total = int(item.qty) * int(item.price or 0)
    except Exception:
        pass

    return JsonResponse({
        "ok": True,
        "item_id": item.id,
        "price": item.price,
        "item_total": item_total,
        "subtotal": subtotal,
        "extra20": extra20,
        "total": total,
    })


def _get_event_datetime(kp: Proposal) -> Optional[datetime]:
    dt = getattr(kp, "event_datetime", None)
    if dt:
        return dt

    meta = _notes_json_load(kp)
    raw = (meta.get("event_datetime") or "").strip()
    return _parse_dt_local(raw)


def _maybe_autoclose(kp: Proposal) -> bool:
    """
    Автозавершение через AUTO_CLOSE_HOURS после event_datetime.
    Проверяем при открытии.
    """
    dt = _get_event_datetime(kp)
    if not dt:
        return False

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    if timezone.now() >= dt + timedelta(hours=AUTO_CLOSE_HOURS):
        if kp.status in (STATUS_DRAFT, STATUS_CONFIRMED):
            kp.status = STATUS_SENT
            kp.save(update_fields=["status"])
            return True

    return False


def _redirect_after_add(request, kp_id: int):
    """
    После добавления услуги:
    - если next = /kp/ => открываем builder конкретного КП (чтобы не теряться в списке)
    - иначе возвращаемся обратно (next/referer) и добавляем kp_added=1
    """
    next_url = (request.POST.get("next") or "").strip()

    # "Добавить и открыть" у тебя шлёт /kp/
    if next_url.rstrip("/") == "/kp":
        return redirect("kp:builder", kp_id=kp_id)

    if not next_url:
        next_url = (request.META.get("HTTP_REFERER") or "/").strip()

    if next_url.rstrip("/") == "/kp":
        return redirect("kp:builder", kp_id=kp_id)

    if "kp_added=1" not in next_url:
        sep = "&" if "?" in next_url else "?"
        next_url = f"{next_url}{sep}kp_added=1"

    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("kp:builder", kp_id=kp_id)


def _pick_manager_user() -> Optional[User]:
    return User.objects.filter(is_staff=True).order_by("id").first()


# =========================
# WEB: KP dashboard
# =========================
@login_required
def kp_home(request):
    # CUSTOMER: сразу в builder своего draft
    if not _is_admin(request.user):
        kp = _get_or_create_customer_draft(request.user)
        return redirect("kp:builder", kp_id=kp.id)

    # ADMIN
    active_list = (
        Proposal.objects
        .filter(owner=request.user, status=STATUS_DRAFT)
        .select_related("customer", "template")
        .order_by("-updated_at")
    )

    requests_list = (
        Proposal.objects
        .filter(owner=request.user, status=STATUS_REQUESTED)
        .select_related("customer", "template")
        .order_by("-updated_at")
    )

    history_list = (
        Proposal.objects
        .filter(owner=request.user)
        .exclude(status=STATUS_DRAFT)
        .exclude(status=STATUS_REQUESTED)
        .select_related("customer", "template")
        .order_by("-updated_at")[:50]
    )

    customers = User.objects.filter(is_staff=False).order_by("username")

    tab = (request.GET.get("tab") or "active").strip().lower()
    if tab not in ("active", "requests", "history"):
        tab = "active"

    ctx = {
        "active_list": active_list,
        "requests_list": requests_list,
        "history_list": history_list,
        "customers": customers,
        "tab": tab,
        "is_admin": True,
    }
    return render(request, "kp/admin_kp_home.html", ctx)


@login_required
def kp_detail(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")

        if _maybe_autoclose(kp):
            _clear_active_kp(request)
            messages.info(request, "КП автоматически завершено (прошло 16 часов после начала).")
            return redirect("/kp/?tab=history")

        if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED, STATUS_SENT, STATUS_REJECTED):
            return redirect("kp:kp")

        _set_active_kp(request, kp)
        return redirect("kp:builder", kp_id=kp.id)

    # CUSTOMER
    if kp.customer_id != request.user.id:
        return redirect("kp:kp")

    return redirect("kp:builder", kp_id=kp.id)


@login_required
@require_POST
@transaction.atomic
def kp_select_customer(request):
    if not _is_admin(request.user):
        return redirect("kp:kp")

    customer_id = (request.POST.get("customer_id") or "").strip()
    if not customer_id:
        messages.error(request, "Не выбран клиент.")
        return redirect("kp:kp")

    customer = get_object_or_404(User, id=int(customer_id), is_staff=False)

    force_new = (request.POST.get("force_new") or "").strip().lower() in ("1", "true", "yes", "on")
    kp = _get_or_create_admin_draft(request.user, customer, force_new=force_new)

    _set_active_kp(request, kp)
    return redirect("kp:builder", kp_id=kp.id)


# =========================
# Autosave (и админ, и клиент)
# =========================
@login_required
@require_POST
@transaction.atomic
def kp_autosave(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return JsonResponse({"ok": False, "detail": "forbidden"}, status=403)
        if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED):
            return JsonResponse({"ok": False, "detail": "not editable"}, status=400)
    else:
        if kp.owner_id != request.user.id or kp.customer_id != request.user.id:
            return JsonResponse({"ok": False, "detail": "forbidden"}, status=403)
        if kp.status != STATUS_DRAFT:
            return JsonResponse({"ok": False, "detail": "already sent"}, status=400)

    data = _notes_json_load(kp)

    title = (request.POST.get("title") or "").strip()
    if title:
        kp.title = title

    template_id = (request.POST.get("template_id") or "").strip()
    if template_id:
        tpl = get_object_or_404(KPTemplate, id=int(template_id))
        kp.template = tpl
        if hasattr(kp, "template_snapshot") and hasattr(tpl, "to_snapshot"):
            kp.template_snapshot = tpl.to_snapshot()

    data["event_title"] = (request.POST.get("event_title") or "").strip()

    # ✅ ТРИ РАЗНЫХ ПОЛЯ
    data["event_address"] = (request.POST.get("event_address") or "").strip()
    data["event_address_url"] = (request.POST.get("event_address_url") or "").strip()
    data["drive_url"] = (request.POST.get("drive_url") or "").strip()

    data["event_description"] = (request.POST.get("event_description") or "").strip()

    dt_raw = (request.POST.get("event_datetime") or "").strip()
    data["event_datetime"] = dt_raw

    if dt_raw and hasattr(kp, "event_datetime"):
        dt = _parse_dt_local(dt_raw)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            kp.event_datetime = dt

    _notes_json_save(kp, data)
    kp.save()

    return JsonResponse({"ok": True})

# =========================
# Добавление/удаление услуг
# =========================
@login_required
@require_POST
@transaction.atomic
def add_service_to_active_kp(request, service_id: int):
    # qty из формы (по умолчанию 1)
    try:
        qty = int(request.POST.get("qty", 1))
    except Exception:
        qty = 1
    qty = max(1, qty)

    if _is_admin(request.user):
        kp = _get_active_kp_for_admin(request)
        if not kp:
            messages.error(request, "Нет активного КП. Открой /kp/ и выбери клиента.")
            return redirect("kp:kp")
    else:
        kp = _get_or_create_customer_draft(request.user)

    service_qs = Service.objects.all()
    if not _is_admin(request.user):
        service_qs = service_qs.filter(is_active=True)

    service = get_object_or_404(service_qs, id=service_id)

    # если услуга одноразовая, qty всегда 1 и не наращиваем повторно
    if not getattr(service, "allow_multiple", True):
        item, created = ProposalItem.objects.get_or_create(
            proposal=kp,
            service=service,
            defaults={"qty": 1, "price": service.base_price or 0},
        )
        if not created and item.qty != 1:
            item.qty = 1
            item.save(update_fields=["qty"])
        return _redirect_after_add(request, kp.id)

    # repeatable: увеличиваем на qty
    item, created = ProposalItem.objects.get_or_create(
        proposal=kp,
        service=service,
        defaults={"qty": qty, "price": service.base_price or 0},
    )
    if not created:
        item.qty += qty
        item.save(update_fields=["qty"])

    return _redirect_after_add(request, kp.id)


@login_required
@require_POST
@transaction.atomic
def add_service_to_kp(request, kp_id: int, service_id: int):
    if not _is_admin(request.user):
        return redirect("kp:kp")

    # qty из формы (по умолчанию 1)
    try:
        qty = int(request.POST.get("qty", 1))
    except Exception:
        qty = 1
    qty = max(1, qty)

    kp = get_object_or_404(Proposal, id=kp_id, owner=request.user, status=STATUS_DRAFT)
    _set_active_kp(request, kp)

    service = get_object_or_404(Service.objects.all(), id=service_id)

    # если услуга одноразовая, qty всегда 1 и не наращиваем повторно
    if not getattr(service, "allow_multiple", True):
        item, created = ProposalItem.objects.get_or_create(
            proposal=kp,
            service=service,
            defaults={"qty": 1, "price": service.base_price or 0},
        )
        if not created and item.qty != 1:
            item.qty = 1
            item.save(update_fields=["qty"])
        return _redirect_after_add(request, kp.id)

    # repeatable: увеличиваем на qty
    item, created = ProposalItem.objects.get_or_create(
        proposal=kp,
        service=service,
        defaults={"qty": qty, "price": service.base_price or 0},
    )
    if not created:
        item.qty += qty
        item.save(update_fields=["qty"])

    return _redirect_after_add(request, kp.id)


@login_required
@require_POST
def remove_item_from_active_kp(request, item_id: int):
    if _is_admin(request.user):
        kp = _get_active_kp_for_admin(request)
        if not kp:
            return redirect("kp:kp")
    else:
        kp = (
            Proposal.objects
            .filter(customer=request.user, owner=request.user, status=STATUS_DRAFT)
            .order_by("-updated_at", "-id")
            .first()
        )
        if not kp:
            return redirect("kp:kp")

    item = get_object_or_404(ProposalItem, id=item_id, proposal=kp)
    item.delete()
    return redirect(request.META.get("HTTP_REFERER") or "/kp/")


@login_required
@require_POST
def clear_kp(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")
        if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED):
            return redirect("kp:kp")
    else:
        if kp.owner_id != request.user.id or kp.customer_id != request.user.id:
            return redirect("kp:kp")
        if kp.status != STATUS_DRAFT:
            return redirect("kp:kp")

    kp.items.all().delete()
    return redirect(request.META.get("HTTP_REFERER") or "/kp/")


# =========================
# Submit: admin завершает, client отправляет
# =========================
@login_required
@require_POST
@transaction.atomic
def submit_kp(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    # ADMIN
    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")

        if kp.items.count() == 0:
            messages.error(request, "Нельзя завершить пустое КП.")
            return redirect("kp:builder", kp_id=kp.id)
        
        items = list(kp.items.all())
        subtotal, extra20, total = _calc_totals(items, add_percent=20)

        kp.fixed_subtotal = subtotal
        kp.fixed_extra = extra20
        kp.fixed_total = total

        kp.status = STATUS_SENT
        kp.save(update_fields=["status", "fixed_subtotal", "fixed_extra", "fixed_total"])
        _clear_active_kp(request)

        next_url = (request.POST.get("next") or "").strip()
        return redirect(next_url or "/kp/?tab=history")

    # CUSTOMER
    if kp.owner_id != request.user.id or kp.customer_id != request.user.id:
        return redirect("kp:kp")

    if kp.status != STATUS_DRAFT:
        messages.info(request, "КП уже отправлено менеджеру. Ждите ответа.")
        return redirect("kp:kp")

    if kp.items.count() == 0:
        messages.error(request, "Сначала добавь услуги.")
        return redirect("kp:builder", kp_id=kp.id)

    manager = _pick_manager_user()
    if not manager:
        messages.error(request, "Нет менеджера (is_staff=True). Создай админа.")
        return redirect("kp:builder", kp_id=kp.id)

    data = _notes_json_load(kp)
    data["customer_requested_at"] = timezone.now().isoformat()
    data["customer_username"] = request.user.username
    data["customer_email"] = getattr(request.user, "email", "") or ""
    data["customer_phone"] = getattr(request.user, "phone", "") or ""
    data["customer_full_name"] = getattr(request.user, "full_name", "") or ""
    _notes_json_save(kp, data)

    kp.owner = manager
    items = list(kp.items.all())
    subtotal, extra20, total = _calc_totals(items, add_percent=20)

    kp.fixed_subtotal = subtotal
    kp.fixed_extra = extra20
    kp.fixed_total = total
    kp.status = STATUS_REQUESTED
    kp.save(update_fields=["status", "fixed_subtotal", "fixed_extra", "fixed_total"])

    messages.success(request, "КП отправлено менеджеру. Ожидай обратной связи.")
    return redirect("kp:kp")


# =========================
# Admin: accept/reject requests
# =========================
@login_required
@require_POST
@transaction.atomic
def kp_request_accept(request, kp_id: int):
    if not _is_admin(request.user):
        return redirect("kp:kp")

    kp = get_object_or_404(Proposal, id=kp_id, owner=request.user, status=STATUS_REQUESTED)
    kp.status = STATUS_DRAFT
    kp.save(update_fields=["status"])
    _set_active_kp(request, kp)

    return redirect("kp:builder", kp_id=kp.id)


@login_required
@require_POST
@transaction.atomic
def kp_request_reject(request, kp_id: int):
    if not _is_admin(request.user):
        return redirect("kp:kp")

    kp = get_object_or_404(Proposal, id=kp_id, owner=request.user, status=STATUS_REQUESTED)
    kp.status = STATUS_REJECTED
    kp.save(update_fields=["status"])
    return redirect("/kp/?tab=requests")


from django.utils import timezone

@login_required
@require_POST
@transaction.atomic
def kp_make_active(request, kp_id: int):
    if not _is_admin(request.user):
        return redirect("kp:kp")

    kp = get_object_or_404(Proposal, id=kp_id, owner=request.user)

    # заявки активируются через "Принять"
    if kp.status == STATUS_REQUESTED:
        messages.info(request, "Это заявка. Нажми “Принять”, чтобы сделать её активной.")
        return redirect("/kp/?tab=requests")

    # 1) делаем снова черновиком
    kp.status = STATUS_DRAFT

    # 2) СБРОС ТАЙМЕРА: считаем, что мероприятие "прямо сейчас"
    now = timezone.now()

    # если поле event_datetime есть в модели — обновляем его
    if hasattr(kp, "event_datetime"):
        kp.event_datetime = now

    # и обновляем meta.notes (чтобы в builder.html было корректное значение в datetime-local)
    data = _notes_json_load(kp)

    # datetime-local обычно ждёт формат "YYYY-MM-DDTHH:MM"
    local = timezone.localtime(now)
    data["event_datetime"] = local.strftime("%Y-%m-%dT%H:%M")

    _notes_json_save(kp, data)

    # 3) сохраняем
    fields = ["status", "notes"]
    if hasattr(kp, "event_datetime"):
        fields.append("event_datetime")
    kp.save(update_fields=fields)

    # 4) активное в сессию и в билд
    _set_active_kp(request, kp)
    messages.success(request, "КП активировано. Таймер мероприятия сброшен на текущее время.")
    return redirect("kp:builder", kp_id=kp.id)


# =========================
# Builder
# =========================
@login_required
def kp_builder(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    is_admin = _is_admin(request.user)

    # ===== Автозакрытие (только для админа и только если КП принадлежит ему) =====
    if is_admin and kp.owner_id == request.user.id:
        if _maybe_autoclose(kp):
            _clear_active_kp(request)
            messages.info(request, "КП автоматически завершено (прошло 16 часов после начала).")
            return redirect("/kp/?tab=history")

    # ===== ADMIN =====
    if is_admin:
        # права админа: только свои КП
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")

        # редактируемо только если DRAFT или REQUESTED
        is_editable = kp.status in (STATUS_DRAFT, STATUS_REQUESTED)

        # делаем активным в сессии даже если read-only (чтобы add_service_to_active_kp понимал контекст)
        _set_active_kp(request, kp)

        items = kp.items.select_related("service").all()
        templates = KPTemplate.objects.order_by("-updated_at").all()
        meta = _notes_json_load(kp)
        subtotal, extra20, total = _calc_totals(items, add_percent=20)

        return render(request, "kp/builder.html", {
            "kp": kp,
            "items": items,
            "templates": templates,
            "meta": meta,
            "subtotal": subtotal,
            "extra20": extra20,
            "total": total,
            "is_admin": True,
            "is_editable": is_editable,   # <-- ВАЖНО: иначе всё становится read-only
        })

    # ===== CUSTOMER =====
    # клиент может открывать только своё КП
    if kp.customer_id != request.user.id:
        return redirect("kp:kp")

    # клиент редактирует только “свой черновик-корзину”: owner=customer=self и статус DRAFT
    is_editable = (
        kp.status == STATUS_DRAFT
        and kp.owner_id == request.user.id
        and kp.customer_id == request.user.id
    )

    if not is_editable:
        messages.info(request, "КП уже отправлено менеджеру. Редактирование выключено.")
        return redirect("kp:kp")

    items = kp.items.select_related("service").all()
    templates = KPTemplate.objects.order_by("-updated_at").all()
    meta = _notes_json_load(kp)
    subtotal, extra20, total = _calc_totals(items, add_percent=20)

    return render(request, "kp/builder.html", {
        "kp": kp,
        "items": items,
        "templates": templates,
        "meta": meta,
        "subtotal": subtotal,
        "extra20": extra20,
        "total": total,
        "is_admin": False,
        "is_editable": True,
    })


# =========================
# PRINT / PDF (Playwright-only, без WeasyPrint)
# =========================
@login_required
def kp_print(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    # Права
    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")
    else:
        if kp.customer_id != request.user.id:
            return redirect("kp:kp")

    items = list(kp.items.select_related("service").all())
    meta = _notes_json_load(kp)

    # --- Заказчик из meta, иначе из профиля ---
    customer_full_name = (meta.get("customer_full_name") or "").strip()
    customer_phone = (meta.get("customer_phone") or "").strip()
    customer_email = (meta.get("customer_email") or "").strip()

    if not customer_full_name:
        if hasattr(kp.customer, "get_full_name"):
            customer_full_name = kp.customer.get_full_name().strip()
        if not customer_full_name:
            fn = getattr(kp.customer, "first_name", "")
            ln = getattr(kp.customer, "last_name", "")
            customer_full_name = f"{fn} {ln}".strip()

    if not customer_full_name:
        customer_full_name = kp.customer.username

    if not customer_phone:
        customer_phone = (getattr(kp.customer, "phone", "") or "").strip()

    if not customer_email:
        customer_email = (getattr(kp.customer, "email", "") or "").strip()

    # --- Исполнитель из settings, иначе из owner ---
    performer_name = (getattr(settings, "KP_PERFORMER_NAME", "") or "").strip()
    performer_phone = (getattr(settings, "KP_PERFORMER_PHONE", "") or "").strip()
    performer_email = (getattr(settings, "KP_PERFORMER_EMAIL", "") or "").strip()

    if not performer_name:
        performer_name = (getattr(kp.owner, "get_full_name", lambda: "")() or kp.owner.username or "").strip()
    if not performer_phone:
        performer_phone = (getattr(kp.owner, "phone", "") or "").strip()
    if not performer_email:
        performer_email = (getattr(kp.owner, "email", "") or "").strip()

    # --- Итоги по строкам ---
    if kp.fixed_total is not None and kp.fixed_total > 0:
        subtotal = kp.fixed_subtotal
        extra20 = kp.fixed_extra
        total = kp.fixed_total
    else:
        subtotal, extra20, total = _calc_totals(items, add_percent=20)

    download = (request.GET.get("download") or "").strip().lower() in ("1", "true", "yes", "on")

    # База сайта для абсолютных ссылок на /media и /static
    site_url = request.build_absolute_uri("/")[:-1]  # например http://127.0.0.1:8000

    ctx = {
        "kp": kp,
        "items": items,
        "meta": meta,
        "subtotal": subtotal,
        "extra20": extra20,
        "total": total,
        "now": timezone.now(),

        "customer_full_name": customer_full_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,

        "performer_name": performer_name,
        "performer_phone": performer_phone,
        "performer_email": performer_email,

        "site_url": site_url,
        
        
    }
 
    ctx["site_url"] = request.build_absolute_uri("/")[:-1]
    ctx["now"] = timezone.now()
   

    # Обычный просмотр HTML
    if not download:
        return render(request, "kp/print.html", ctx)

    # ========= PDF через Playwright =========
    html_string = render_to_string("kp/print.html", ctx, request=request)
    filename = f"KP_{kp.id}.pdf"

    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Важно: чтобы относительные ссылки нормально резолвились,
            # добавим <base href="..."> прямо в HTML (надёжнее, чем надеяться на base_url API).
            if "<head>" in html_string:
                html_string = html_string.replace(
                    "<head>",
                    f"<head><base href=\"{site_url}/\">",
                    1
                )

            page.set_content(html_string, wait_until="load")

            # Иногда шрифты/картинки догружаются не мгновенно
            page.wait_for_timeout(400)

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
            )

            browser.close()

        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["Cache-Control"] = "no-store"
        return resp

    except Exception as e:
        return HttpResponse(
            "PDF генерация не работает через Playwright.\n"
            f"Ошибка: {e}\n\n"
            "Проверь команды:\n"
            "  python -m pip install playwright\n"
            "  python -m playwright install chromium\n",
            content_type="text/plain; charset=utf-8",
            status=500,
        )



# =========================
# API под fetch() из category_services.html
# =========================
def _json_body(request) -> dict:
    try:
        raw = request.body.decode("utf-8") or ""
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


@login_required
@require_POST
@transaction.atomic
def api_add_service_to_active_kp(request):
    payload = _json_body(request)
    service_id = payload.get("service_id")
    qty_raw = payload.get("qty", 1)

    try:
        qty = int(qty_raw)
    except Exception:
        return JsonResponse({"ok": False, "detail": "qty должен быть числом"}, status=400)

    if not service_id:
        return JsonResponse({"ok": False, "detail": "service_id обязателен"}, status=400)
    if qty <= 0:
        return JsonResponse({"ok": False, "detail": "qty должен быть > 0"}, status=400)

    service_qs = Service.objects.all()
    if not _is_admin(request.user):
        service_qs = service_qs.filter(is_active=True)
    service = get_object_or_404(service_qs, id=int(service_id))

    if _is_admin(request.user):
        kp = _get_active_kp_for_admin(request)
        if not kp:
            return JsonResponse(
                {"ok": False, "detail": "Нет активного КП в сессии (выбери клиента в /kp/)."},
                status=400
            )
    else:
        kp = _get_or_create_customer_draft(request.user)

    item, created = ProposalItem.objects.get_or_create(
        proposal=kp,
        service=service,
        defaults={"qty": qty, "price": service.base_price or 0},
    )
    if not created:
        item.qty = qty
        item.save(update_fields=["qty"])

    return JsonResponse({"ok": True, "kp_id": kp.id, "item_id": item.id})


@login_required
@require_POST
@transaction.atomic
def api_add_service_to_kp(request, kp_id: int):
    if not _is_admin(request.user):
        return JsonResponse({"ok": False, "detail": "forbidden"}, status=403)

    kp = get_object_or_404(Proposal, id=kp_id, owner=request.user, status=STATUS_DRAFT)
    _set_active_kp(request, kp)

    payload = _json_body(request)
    service_id = payload.get("service_id")
    qty_raw = payload.get("qty", 1)

    try:
        qty = int(qty_raw)
    except Exception:
        return JsonResponse({"ok": False, "detail": "qty должен быть числом"}, status=400)

    if not service_id:
        return JsonResponse({"ok": False, "detail": "service_id обязателен"}, status=400)
    if qty <= 0:
        return JsonResponse({"ok": False, "detail": "qty должен быть > 0"}, status=400)

    service = get_object_or_404(Service.objects.all(), id=int(service_id))

    item, created = ProposalItem.objects.get_or_create(
        proposal=kp,
        service=service,
        defaults={"qty": qty, "price": service.base_price or 0},
    )
    if not created:
        item.qty = qty
        item.save(update_fields=["qty"])

    return JsonResponse({"ok": True, "kp_id": kp.id, "item_id": item.id})


@login_required
@require_POST
@transaction.atomic
def kp_upload_photo(request, kp_id: int):
    kp = get_object_or_404(Proposal, id=kp_id)

    # Права
    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return redirect("kp:kp")
        if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED):
            return redirect("kp:kp")
    else:
        if kp.owner_id != request.user.id or kp.customer_id != request.user.id or kp.status != STATUS_DRAFT:
            return redirect("kp:kp")

    file = request.FILES.get("photo")
    if not file:
        messages.error(request, "Файл не выбран.")
        return redirect("kp:builder", kp_id=kp.id)

    # Поле должно существовать в модели Proposal
    if not hasattr(kp, "photo"):
        messages.error(request, "В модели Proposal нет поля photo. Добавь ImageField photo.")
        return redirect("kp:builder", kp_id=kp.id)

    kp.photo = file
    kp.save(update_fields=["photo"])
    messages.success(request, "Фото загружено.")
    return redirect("kp:builder", kp_id=kp.id)


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Proposal as KP, ProposalItem as KPItem


from .models import ProposalItem

@require_POST
def update_item_qty(request, item_id):
    try:
        action = request.POST.get("action")  # inc / dec
        item = get_object_or_404(ProposalItem, id=item_id)

        if action == "inc":
            item.qty += 1
        elif action == "dec":
            item.qty = max(1, item.qty - 1)
        else:
            return JsonResponse({"ok": False, "error": "Invalid action"}, status=400)

        item.save()

        proposal = item.proposal

        return JsonResponse({
            "ok": True,
            "qty": item.qty,
            "item_total": float(item.total_price),
            "proposal_total": float(proposal.total_amount),
        })

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import Proposal as KP, ProposalItem as KPItem  # алиасы

@login_required
@require_POST
@transaction.atomic
def update_item_qty(request, item_id: int):
    item = get_object_or_404(ProposalItem.objects.select_related("proposal"), id=item_id)
    kp = item.proposal

    # доступ: админ-владелец или клиент-владелец (как у тебя было)
    if request.user.id not in (kp.owner_id, kp.customer_id):
        return JsonResponse({"ok": False, "error": "Нет доступа"}, status=403)

    # НО: клиенту можно менять qty только в своём draft, админ - в draft/requested
    if _is_admin(request.user):
        if kp.owner_id != request.user.id:
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        if kp.status not in (STATUS_DRAFT, STATUS_REQUESTED):
            return JsonResponse({"ok": False, "error": "not editable"}, status=400)
    else:
        if not (kp.status == STATUS_DRAFT and kp.owner_id == request.user.id and kp.customer_id == request.user.id):
            return JsonResponse({"ok": False, "error": "not editable"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    action = (payload.get("action") or "").strip().lower()
    if action not in ("inc", "dec"):
        return JsonResponse({"ok": False, "error": "Неверное действие"}, status=400)

    if action == "inc":
        item.qty = item.qty + 1
    else:
        item.qty = max(1, item.qty - 1)

    item.save(update_fields=["qty"])

    # totals
    items = list(kp.items.all())
    subtotal, extra20, total = _calc_totals(items, add_percent=20)

    item_total = 0
    try:
        item_total = int(item.qty) * int(item.price or 0)
    except Exception:
        pass

    return JsonResponse({
        "ok": True,
        "item_id": item.id,
        "qty": item.qty,
        "item_total": item_total,
        "subtotal": subtotal,
        "extra20": extra20,
        "total": total,
    })


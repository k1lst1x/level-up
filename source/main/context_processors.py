from __future__ import annotations

from django.urls import reverse

from catalog.models import Service


def nav_services_url(request):
    """
    Глобальная ссылка в navbar на первую доступную категорию с услугами
    (страница /categories/<id>/services/) без хардкода id.
    """
    qs = Service.objects.order_by("category__sort_order", "category_id", "sort_order", "id")

    is_admin = bool(
        getattr(request, "user", None)
        and request.user.is_authenticated
        and (request.user.is_staff or request.user.is_superuser)
    )

    if not is_admin:
        qs = qs.filter(is_active=True, category__is_active=True)

    category_id = qs.values_list("category_id", flat=True).first()
    if category_id:
        return {"nav_services_url": reverse("main:category_services", args=[category_id])}

    # Фолбэк, если услуг пока нет в БД.
    return {"nav_services_url": reverse("main:categories")}

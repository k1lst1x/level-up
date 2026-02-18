# portfolio/views.py
from django.shortcuts import get_object_or_404, render

from .models import PortfolioCase, PortfolioCategory


def portfolio_list(request):
    categories = PortfolioCategory.objects.filter(is_active=True)
    cases_qs = PortfolioCase.objects.filter(is_active=True).select_related("category").prefetch_related("photos")

    active_cat = None
    cat_id = request.GET.get("category")
    if cat_id:
        try:
            active_cat = int(cat_id)
            cases_qs = cases_qs.filter(category_id=active_cat)
        except (ValueError, TypeError):
            active_cat = None

    return render(request, "portfolio/list.html", {
        "categories": categories,
        "cases": cases_qs,
        "active_cat": active_cat,
    })


def portfolio_detail(request, pk):
    case = get_object_or_404(PortfolioCase, pk=pk, is_active=True)
    photos = case.photos.all()

    return render(request, "portfolio/detail.html", {
        "case": case,
        "photos": photos,
    })

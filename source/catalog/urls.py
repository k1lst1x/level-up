# catalog/urls.py
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryListViewSet, CategoryServicesAPIView

router = DefaultRouter()
router.register(r"categories", CategoryListViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
    path("categories/<int:category_id>/services/", CategoryServicesAPIView.as_view(), name="category-services"),
]

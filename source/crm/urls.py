# crm/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CRMUserViewSet

router = DefaultRouter()
router.register(r"users", CRMUserViewSet, basename="crm-users")

urlpatterns = [
    path("", include(router.urls)),
]

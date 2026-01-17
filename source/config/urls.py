# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),

    path("", include("main.urls")),

    # KP (WEB + API внутри kp.urls)
    path("kp/", include("kp.urls")),

    # API
    path("api/", include("catalog.urls")),
    path("api/", include("crm.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# main/urls.py
from django.urls import path
from django.views.generic import TemplateView
from .views import (
    home,
    categories_page,
    category_services_page,
    crm_page,
)

app_name = "main"

urlpatterns = [
    path("", home, name="home"),
    path("categories/", categories_page, name="categories"),

    # сразу услуги по категории, без подкатегорий
    path(
        "categories/<int:category_id>/services/",
        category_services_page,
        name="category_services",
    ),

    path("crm/", crm_page, name="crm"),
    path("kp-examples/", TemplateView.as_view(template_name="main/kp_examples.html"), name="kp_examples"),
]

# kp/urls.py
from django.urls import path

from . import views

app_name = "kp"

urlpatterns = [
    path("", views.kp_home, name="kp"),
    path("<int:kp_id>/", views.kp_detail, name="detail"),

    # builder
    path("<int:kp_id>/builder/", views.kp_builder, name="builder"),
    path("<int:kp_id>/autosave/", views.kp_autosave, name="autosave"),
    path("<int:kp_id>/upload-photo/", views.kp_upload_photo, name="upload_photo"),

    # add/remove/clear
    path("add/<int:service_id>/", views.add_service_to_active_kp, name="add_to_active"),
    path("<int:kp_id>/add/<int:service_id>/", views.add_service_to_kp, name="add_to_kp"),
    path("remove-item/<int:item_id>/", views.remove_item_from_active_kp, name="remove_item"),
    path("<int:kp_id>/clear/", views.clear_kp, name="clear"),

    # submit
    path("<int:kp_id>/submit/", views.submit_kp, name="submit"),

    # requests
    path("<int:kp_id>/request-accept/", views.kp_request_accept, name="request_accept"),
    path("<int:kp_id>/request-reject/", views.kp_request_reject, name="request_reject"),

    # make active (from history)
    path("<int:kp_id>/make-active/", views.kp_make_active, name="make_active"),

    # choose customer (admin)
    path("select-customer/", views.kp_select_customer, name="select_customer"),

    # print/pdf
    path("<int:kp_id>/print/", views.kp_print, name="print"),

    path("item/<int:item_id>/qty/", views.update_item_qty, name="update_item_qty"),
    path("item/<int:item_id>/price/", views.update_item_price, name="update_item_price"),
]

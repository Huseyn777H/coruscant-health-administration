from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    CHAloginView,
    approval_queue,
    create_order,
    create_report,
    dashboard,
    download_document,
    emergency_intake,
    healthcheck,
    landing,
    register,
    submit_reading,
    upload_document,
    upload_order_result,
)

urlpatterns = [
    path("", landing, name="landing"),
    path("health/", healthcheck, name="healthcheck"),
    path("login/", CHAloginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("readings/new/", submit_reading, name="submit_reading"),
    path("reports/new/", create_report, name="create_report"),
    path("orders/new/", create_order, name="create_order"),
    path("orders/<int:order_id>/result/", upload_order_result, name="upload_order_result"),
    path("approvals/", approval_queue, name="approval_queue"),
    path("emergency/intake/", emergency_intake, name="emergency_intake"),
    path("documents/upload/", upload_document, name="upload_document"),
    path("documents/<int:document_id>/download/", download_document, name="download_document"),
]

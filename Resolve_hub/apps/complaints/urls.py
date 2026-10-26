from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("complaints/", views.complaint_list, name="list"),
    path("complaints/new/", views.complaint_create, name="create"),
    path("complaints/ocr/", views.ocr_intake_view, name="ocr_upload"),
    path("complaints/official/", views.official_matter_create_view, name="official_create"),
    path("complaints/<str:public_id>/", views.complaint_detail, name="detail"),
    path("complaints/<str:public_id>/attachments/upload/", views.attachment_upload, name="attachment_upload"),
    path("attachments/<int:attachment_id>/download/", views.attachment_download, name="attachment_download"),
    path("track/", views.public_tracker, name="tracker"),
]

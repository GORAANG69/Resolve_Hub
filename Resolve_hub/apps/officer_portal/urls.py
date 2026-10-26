from django.urls import path
from . import views

app_name = "officer_portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("complaints/<int:pk>/", views.complaint_detail, name="complaint_detail"),
]

from django.urls import path
from . import views

app_name = "command_centre"

urlpatterns = [
    path("", views.command_centre_dashboard, name="dashboard"),
    path("export/csv/", views.export_cases_csv, name="export_csv"),
    path("risk/", views.risk_leaderboard_view, name="risk_leaderboard"),
    path("risk/heatmap-data/", views.risk_heatmap_data, name="risk_heatmap_data"),
]

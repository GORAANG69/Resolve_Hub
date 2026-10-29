from django.urls import path
from . import api_views, views

app_name = "command_centre"

urlpatterns = [
    path("", views.command_centre_dashboard, name="dashboard"),
    path("export/csv/", views.export_cases_csv, name="export_csv"),
    path("risk/", views.risk_leaderboard_view, name="risk_leaderboard"),
    path("risk/heatmap-data/", views.risk_heatmap_data, name="risk_heatmap_data"),

    # REST APIs for Command Centre, AI Intelligence, SLA Monitoring & Case Management
    path("api/dashboard/metrics/", api_views.api_dashboard_metrics, name="api_metrics"),
    path("api/cases/", api_views.api_cases_list, name="api_cases"),
    path("api/cases/<str:case_id>/", api_views.api_case_detail, name="api_case_detail"),
    path("api/cases/<str:case_id>/action/", api_views.api_case_action, name="api_case_action"),
    path("api/theme/", api_views.api_theme_preference, name="api_theme"),
]

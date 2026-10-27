from django.urls import path
from . import views

app_name = "command_centre"

urlpatterns = [
    path("", views.command_centre_dashboard, name="dashboard"),
    path("export/csv/", views.export_cases_csv, name="export_csv"),
    path("risk/", views.risk_leaderboard_view, name="risk_leaderboard"),
    path("risk/heatmap-data/", views.risk_heatmap_data, name="risk_heatmap_data"),
    path("api/citizen-grievances/", views.citizen_grievances_api, name="citizen_grievances_api"),
    path("api/student-feedback/", views.student_feedback_api, name="student_feedback_api"),
    path("api/analytics-summary/", views.real_datasets_analytics_api, name="analytics_summary_api"),
]

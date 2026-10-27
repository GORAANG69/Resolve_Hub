from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.command_centre.urls")),
    path("command-centre/", RedirectView.as_view(url="/", permanent=False)),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("apps.accounts.urls")),
    path("complaints/", include("apps.complaints.urls")),
    path("officer/", include("apps.officer_portal.urls")),
    path("", include("apps.director_portal.urls")),
    path("", include("apps.hod_portal.urls")),
]

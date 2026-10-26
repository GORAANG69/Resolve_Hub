from django.shortcuts import redirect
from apps.officer_portal.permissions import officer_required


@officer_required
def dashboard(request):
    return redirect("officer_portal:dashboard")


@officer_required
def complaint_detail(request, pk: int):
    return redirect("officer_portal:complaint_detail", pk=pk)

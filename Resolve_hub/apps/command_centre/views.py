import csv
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.complaints.models import ComplaintCategory, PriorityLevel, SourceChannel, Status
from apps.institutions.models import Bureau, Cell, Institution, InstitutionRiskScore, InstitutionType
from apps.officer_portal.permissions import officer_required

from .services import compute_command_centre_metrics, get_command_centre_queryset


@officer_required
def command_centre_dashboard(request):
    """
    Unified Command Centre dashboard for AICTE leadership and officers:
    Director, Member Secretary, Bureau Heads, and Section Heads.
    """
    params = request.GET.dict()
    base_qs = get_command_centre_queryset(request.user, params)

    metrics = compute_command_centre_metrics(request.user, base_qs)

    # Paginate complaints table
    paginator = Paginator(base_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Filter dropdown choices
    bureaus = Bureau.objects.filter(is_active=True)
    cells = Cell.objects.filter(is_active=True)
    categories = ComplaintCategory.objects.filter(is_active=True)
    states = (
        Institution.objects.filter(is_active=True)
        .values_list("state", flat=True)
        .distinct()
        .order_by("state")
    )

    context = {
        "kpis": metrics["kpis"],
        "charts": metrics["charts"],
        "recent_alerts": metrics["recent_alerts"],
        "page_obj": page_obj,
        "bureaus": bureaus,
        "cells": cells,
        "categories": categories,
        "states": states,
        "priorities": PriorityLevel.choices,
        "statuses": Status.choices,
        "channels": SourceChannel.choices,
        "types": InstitutionType.choices,
        "selected_filters": params,
    }
    return render(request, "command_centre/dashboard.html", context)


@officer_required
def export_cases_csv(request):
    """
    CSV export of filtered case list.
    STRICT PRIVACY RULE: Complainant personal identity (name, email, roll number, mobile)
    is excluded for officer roles (SECTION_HEAD, BUREAU_HEAD, etc.); only Director/Admin may export identity.
    """
    params = request.GET.dict()
    base_qs = get_command_centre_queryset(request.user, params)

    can_see_identity = request.user.role in (Role.DIRECTOR, Role.ADMIN)

    response = HttpResponse(content_type="text/csv")
    filename = f"resolvehub_cases_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    headers = [
        "Case ID",
        "Institution",
        "AICTE ID",
        "State",
        "Cell",
        "Category",
        "Subject",
        "Priority",
        "Status",
        "Lifecycle Stage",
        "Channel",
        "SLA Due At",
        "Escalation Level",
        "Court/RTI",
        "Created At",
    ]
    if can_see_identity:
        headers.extend(["Complainant Name", "Complainant Email", "Complainant Mobile"])

    writer.writerow(headers)

    for c in base_qs:
        row = [
            c.complaint_code,
            c.institution.name if c.institution else "General",
            c.institution.aicte_id if c.institution else "-",
            c.institution.state if c.institution else "-",
            c.cell.name if c.cell else "Unassigned",
            c.category.name if c.category else "-",
            c.subject,
            c.priority,
            c.status,
            c.lifecycle_stage,
            c.source_channel,
            c.sla_due_at.strftime("%Y-%m-%d %H:%M") if c.sla_due_at else "-",
            f"L{c.escalation_level}",
            "Yes" if c.is_court_rti else "No",
            c.created_at.strftime("%Y-%m-%d %H:%M"),
        ]
        if can_see_identity:
            if c.is_confidential and request.user.role != Role.ADMIN:
                row.extend(["[CONFIDENTIAL]", "[CONFIDENTIAL]", "[CONFIDENTIAL]"])
            else:
                row.extend([
                    c.student.full_name or "-",
                    c.student.email or "-",
                    c.student.mobile_number or "-",
                ])
        writer.writerow(row)

    log_action(
        actor=request.user,
        action="CASES_CSV_EXPORTED",
        target="cases:all",
        metadata={"count": base_qs.count(), "included_identity": can_see_identity},
    )

    return response


# ---------------------------------------------------------------------------
# Section 7: Risk Radar Views
# ---------------------------------------------------------------------------
@officer_required
def risk_leaderboard_view(request):
    """
    Institutional Risk Radar leaderboard: ranks institutions by risk score
    with explainable component breakdowns (volume, severity, repeat, SLA breach, court/RTI).
    """
    scores = (
        InstitutionRiskScore.objects.select_related("institution")
        .order_by("-score")[:50]
    )

    return render(
        request,
        "command_centre/risk_leaderboard.html",
        {"scores": scores},
    )


@officer_required
def risk_heatmap_data(request):
    """
    JSON endpoint for state and institutional heat distribution.
    Never includes complainant PII.
    """
    state_counts = {}
    inst_data = []

    scores = InstitutionRiskScore.objects.select_related("institution").order_by("-score")

    for s in scores:
        inst = s.institution
        st = inst.state or "Other"
        state_counts[st] = state_counts.get(st, 0) + 1

        inst_data.append({
            "aicte_id": inst.aicte_id,
            "name": inst.name,
            "state": inst.state,
            "district": inst.district,
            "score": s.score,
            "band": s.band,
            "components": s.components,
        })

    return JsonResponse({
        "by_state": state_counts,
        "institutions": inst_data,
    })

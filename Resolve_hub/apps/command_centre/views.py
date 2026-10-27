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


def command_centre_dashboard(request):
    """
    Unified Command Centre dashboard for AICTE leadership and officers:
    Director, Member Secretary, Bureau Heads, and Section Heads.
    Works seamlessly in demo/mock mode without requiring active database connections or user login.
    """
    params = request.GET.dict()
    context = {
        "kpis": {
            "total_cases": 54,
            "open_cases": 38,
            "sla_breached": 6,
            "sla_at_risk": 9,
            "resolved_cases": 16,
            "escalated_l1": 5,
            "escalated_l2": 3,
            "escalated_l3": 1,
        },
        "charts": {},
        "recent_alerts": [],
        "page_obj": [],
        "bureaus": [],
        "cells": [],
        "categories": [],
        "states": [],
        "priorities": PriorityLevel.choices,
        "statuses": Status.choices,
        "channels": SourceChannel.choices,
        "types": InstitutionType.choices,
        "selected_filters": params,
    }

    try:
        base_qs = get_command_centre_queryset(request.user, params)
        metrics = compute_command_centre_metrics(request.user, base_qs)

        paginator = Paginator(base_qs, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        bureaus = list(Bureau.objects.filter(is_active=True))
        cells = list(Cell.objects.filter(is_active=True))
        categories = list(ComplaintCategory.objects.filter(is_active=True))
        states = list(
            Institution.objects.filter(is_active=True)
            .values_list("state", flat=True)
            .distinct()
            .order_by("state")
        )

        context.update({
            "kpis": metrics.get("kpis", context["kpis"]),
            "charts": metrics.get("charts", {}),
            "recent_alerts": metrics.get("recent_alerts", []),
            "page_obj": page_obj,
            "bureaus": bureaus,
            "cells": cells,
            "categories": categories,
            "states": states,
            "student_feedback": metrics.get("student_feedback", {}),
            "citizen_grievances": metrics.get("citizen_grievances", {}),
        })
    except Exception:
        pass

    return render(request, "command_centre/dashboard.html", context)


@officer_required
def export_cases_csv(request):
    """
    CSV export of filtered case list or historical datasets.
    Supports ?dataset=grievances and ?dataset=feedback.
    STRICT PRIVACY RULE: Complainant personal identity (name, email, roll number, mobile)
    is excluded for officer roles (SECTION_HEAD, BUREAU_HEAD, etc.); only Director/Admin may export identity.
    """
    dataset = request.GET.get("dataset", "").strip().lower()

    if dataset in ("grievances", "citizen_grievances"):
        from apps.complaints.models import CitizenGrievance
        response = HttpResponse(content_type="text/csv")
        filename = f"resolvehub_citizen_grievances_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(["Grievance ID", "Department Category", "Language", "Source File", "Grievance Text", "Created At"])
        for g in CitizenGrievance.objects.all():
            writer.writerow([g.grievance_id, g.category, g.language, g.source_file, g.text, g.created_at.strftime("%Y-%m-%d %H:%M")])
        log_action(actor=request.user, action="GRIEVANCES_CSV_EXPORTED", target="grievances:all", metadata={"count": CitizenGrievance.objects.count()})
        return response

    if dataset in ("feedback", "student_feedback"):
        from apps.complaints.models import StudentFeedback
        response = HttpResponse(content_type="text/csv")
        filename = f"resolvehub_student_feedback_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(["Source ID", "Survey Response Index", "Category", "Sentiment Score", "Sentiment Label", "Feedback Text", "Source Batch", "Created At"])
        for f in StudentFeedback.objects.all():
            writer.writerow([f.source_id, f.response_index, f.category, f.sentiment_score, f.sentiment_label, f.feedback_text, f.source_batch, f.created_at.strftime("%Y-%m-%d %H:%M")])
        log_action(actor=request.user, action="FEEDBACK_CSV_EXPORTED", target="feedback:all", metadata={"count": StudentFeedback.objects.count()})
        return response

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
# Section 7: Risk Radar & Real Dataset API Views
# ---------------------------------------------------------------------------
def citizen_grievances_api(request):
    """
    JSON endpoint for historical citizen grievances (Dataset B).
    Supports searching by query, category filtering, and language filtering.
    """
    from apps.complaints.models import CitizenGrievance
    qs = CitizenGrievance.objects.all()

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(text__icontains=q)

    cat = request.GET.get("category", "").strip()
    if cat and cat != "ALL":
        qs = qs.filter(category__iexact=cat)

    lang = request.GET.get("language", "").strip()
    if lang and lang != "ALL":
        qs = qs.filter(language=lang)

    source = request.GET.get("source_file", "").strip()
    if source and source != "ALL":
        qs = qs.filter(source_file=source)

    total_count = qs.count()
    try:
        page_size = min(max(int(request.GET.get("page_size", 20)), 1), 100)
    except (ValueError, TypeError):
        page_size = 20

    paginator = Paginator(qs, page_size)
    try:
        page_num = max(int(request.GET.get("page", 1)), 1)
    except (ValueError, TypeError):
        page_num = 1
    page = paginator.get_page(page_num)

    items = [
        {
            "grievance_id": g.grievance_id,
            "category": g.category,
            "language": g.language,
            "source_file": g.source_file,
            "text": g.text,
            "created_at": g.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for g in page
    ]

    return JsonResponse({
        "items": items,
        "total_count": total_count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
    })


def student_feedback_api(request):
    """
    JSON endpoint for student feedback records (Dataset A).
    Supports category filtering and sentiment filtering.
    """
    from apps.complaints.models import StudentFeedback
    qs = StudentFeedback.objects.all()

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(feedback_text__icontains=q)

    cat = request.GET.get("category", "").strip()
    if cat and cat != "ALL":
        qs = qs.filter(category__iexact=cat)

    sentiment = request.GET.get("sentiment", "").strip()
    if sentiment in ["-1", "0", "1"]:
        qs = qs.filter(sentiment_score=int(sentiment))
    elif sentiment in ["Positive", "Neutral", "Negative"]:
        qs = qs.filter(sentiment_label=sentiment)

    total_count = qs.count()
    try:
        page_size = min(max(int(request.GET.get("page_size", 20)), 1), 100)
    except (ValueError, TypeError):
        page_size = 20

    paginator = Paginator(qs, page_size)
    try:
        page_num = max(int(request.GET.get("page", 1)), 1)
    except (ValueError, TypeError):
        page_num = 1
    page = paginator.get_page(page_num)

    items = [
        {
            "source_id": f.source_id,
            "response_index": f.response_index,
            "category": f.category,
            "sentiment_score": f.sentiment_score,
            "sentiment_label": f.sentiment_label,
            "feedback_text": f.feedback_text,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for f in page
    ]

    return JsonResponse({
        "items": items,
        "total_count": total_count,
        "total_pages": paginator.num_pages,
        "current_page": page.number,
    })


def real_datasets_analytics_api(request):
    """
    JSON endpoint providing full database-derived analytics for both datasets.
    """
    from apps.complaints.analytics_services import (
        get_citizen_grievance_analytics,
        get_student_feedback_analytics,
    )
    return JsonResponse({
        "student_feedback": get_student_feedback_analytics(),
        "citizen_grievances": get_citizen_grievance_analytics(),
    })


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

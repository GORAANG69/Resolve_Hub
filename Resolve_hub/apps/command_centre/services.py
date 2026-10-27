from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Role
from apps.complaints.models import Complaint, EscalationEvent, PriorityLevel, Status
from apps.institutions.models import Bureau, Cell, Institution, InstitutionType
from apps.officer_portal.permissions import get_officer_complaints_queryset


def get_command_centre_queryset(user, params: Dict[str, Any]):
    """
    Apply role scoping and query parameter filters with zero N+1 queries.
    """
    if user and user.is_authenticated and getattr(user, "is_officer", False):
        qs = get_officer_complaints_queryset(user)
    else:
        qs = Complaint.objects.all()

    qs = qs.select_related(
        "institution",
        "cell",
        "cell__bureau",
        "category",
        "student",
        "duplicate_of",
        "institution__risk_score",
    )

    # 1. Search Query (Case ID, Subject, Institution name)
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(complaint_code__icontains=q)
            | Q(subject__icontains=q)
            | Q(institution__name__icontains=q)
            | Q(institution__aicte_id__icontains=q)
        )

    # 2. Bureau & Cell
    bureau_slug = params.get("bureau", "").strip()
    if bureau_slug:
        qs = qs.filter(cell__bureau__slug=bureau_slug)

    cell_slug = params.get("cell", "").strip()
    if cell_slug:
        qs = qs.filter(cell__slug=cell_slug)

    # 3. State & Institution
    state = params.get("state", "").strip()
    if state:
        qs = qs.filter(institution__state__iexact=state)

    inst_id = params.get("institution", "").strip()
    if inst_id and inst_id.isdigit():
        qs = qs.filter(institution_id=int(inst_id))

    inst_type = params.get("institution_type", "").strip()
    if inst_type:
        qs = qs.filter(institution__institution_type=inst_type)

    # 4. Category & Priority
    category_id = params.get("category", "").strip()
    if category_id and category_id.isdigit():
        qs = qs.filter(category_id=int(category_id))

    priority = params.get("priority", "").strip()
    if priority in PriorityLevel.values:
        qs = qs.filter(priority=priority)

    # 5. Status & SLA State
    status = params.get("status", "").strip()
    if status in Status.values:
        qs = qs.filter(status=status)

    sla_state = params.get("sla_state", "").strip()
    now = timezone.now()
    if sla_state == "BREACHED":
        qs = qs.exclude(status__in=[Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]).filter(
            sla_due_at__isnull=False, sla_due_at__lt=now
        )
    elif sla_state == "AT_RISK":
        # At risk: >= 80% elapsed but not yet breached
        active = qs.exclude(status__in=[Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]).filter(
            sla_due_at__isnull=False, sla_due_at__gte=now
        )
        at_risk_ids = []
        for c_id, c_created_at, c_sla_due_at in active.values_list("id", "created_at", "sla_due_at"):
            if c_sla_due_at and c_created_at:
                window = (c_sla_due_at - c_created_at).total_seconds()
                if window > 0 and ((now - c_created_at).total_seconds() / window) >= 0.8:
                    at_risk_ids.append(c_id)
        qs = qs.filter(id__in=at_risk_ids)

    # 6. Channel, Language, Court/RTI, Escalation
    channel = params.get("source_channel", "").strip()
    if channel:
        qs = qs.filter(source_channel=channel)

    lang = params.get("language", "").strip()
    if lang in ["en", "hi"]:
        qs = qs.filter(language=lang)

    court_rti = params.get("is_court_rti", "").strip()
    if court_rti == "1":
        qs = qs.filter(is_court_rti=True)

    esc_level = params.get("escalation_level", "").strip()
    if esc_level and esc_level.isdigit():
        qs = qs.filter(escalation_level=int(esc_level))

    return qs.order_by("-created_at")


def compute_command_centre_metrics(user, base_qs) -> Dict[str, Any]:
    """
    Aggregate metrics and chart breakdowns for Command Centre.
    """
    now = timezone.now()
    total_cases = base_qs.count()

    resolved_count = base_qs.filter(status__in=[Status.RESOLVED, Status.CLOSED]).count()
    open_cases_qs = base_qs.exclude(status__in=[Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM])
    open_count = open_cases_qs.count()

    # Breached cases
    sla_breached_count = open_cases_qs.filter(sla_due_at__isnull=False, sla_due_at__lt=now).count()

    # At-risk cases (80% <= elapsed < 100%)
    at_risk_count = 0
    for c_id, c_created_at, c_sla_due_at in open_cases_qs.filter(
        sla_due_at__isnull=False, sla_due_at__gte=now
    ).values_list("id", "created_at", "sla_due_at"):
        if c_sla_due_at and c_created_at:
            window = (c_sla_due_at - c_created_at).total_seconds()
            if window > 0 and ((now - c_created_at).total_seconds() / window) >= 0.8:
                at_risk_count += 1

    # Escalation levels breakdown
    esc_l1 = base_qs.filter(escalation_level=1).count()
    esc_l2 = base_qs.filter(escalation_level=2).count()
    esc_l3 = base_qs.filter(escalation_level=3).count()

    # Breakdown by Cell
    cell_data = list(
        open_cases_qs.values("cell__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    cell_labels = [item["cell__name"] or "Unassigned" for item in cell_data]
    cell_counts = [item["count"] for item in cell_data]

    # Breakdown by Bureau
    bureau_data = list(
        open_cases_qs.values("cell__bureau__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    bureau_labels = [item["cell__bureau__name"] or "Direct / Unassigned" for item in bureau_data]
    bureau_counts = [item["count"] for item in bureau_data]

    # Breakdown by State
    state_data = list(
        open_cases_qs.values("institution__state")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    state_labels = [item["institution__state"] or "Other" for item in state_data]
    state_counts = [item["count"] for item in state_data]

    # Breakdown by Institution Type
    type_data = list(
        open_cases_qs.values("institution__institution_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    type_labels = [item["institution__institution_type"] or "Other" for item in type_data]
    type_counts = [item["count"] for item in type_data]

    # Breakdown by Category
    category_data = list(
        open_cases_qs.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    category_labels = [item["category__name"] or "Other" for item in category_data]
    category_counts = [item["count"] for item in category_data]

    # Breakdown by Source Channel
    channel_data = list(
        base_qs.values("source_channel")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    channel_labels = [item["source_channel"] for item in channel_data]
    channel_counts = [item["count"] for item in channel_data]

    # Escalation Alerts Feed (latest 10 EscalationEvents scoped to user)
    scoped_complaint_ids = base_qs.values_list("id", flat=True)
    recent_alerts = list(
        EscalationEvent.objects.filter(complaint_id__in=scoped_complaint_ids)
        .select_related("complaint", "complaint__institution", "complaint__cell")
        .order_by("-triggered_at")[:10]
    )

    return {
        "kpis": {
            "total_cases": total_cases,
            "open_cases": open_count,
            "sla_at_risk": at_risk_count,
            "sla_breached": sla_breached_count,
            "resolved_cases": resolved_count,
            "escalated_l1": esc_l1,
            "escalated_l2": esc_l2,
            "escalated_l3": esc_l3,
        },
        "charts": {
            "cell": {"labels": cell_labels, "data": cell_counts},
            "bureau": {"labels": bureau_labels, "data": bureau_counts},
            "state": {"labels": state_labels, "data": state_counts},
            "type": {"labels": type_labels, "data": type_counts},
            "category": {"labels": category_labels, "data": category_counts},
            "channel": {"labels": channel_labels, "data": channel_counts},
        },
        "recent_alerts": recent_alerts,
    }

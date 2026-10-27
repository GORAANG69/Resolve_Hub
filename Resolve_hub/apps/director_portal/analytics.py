"""
Institutional Complaint Trend Analysis Engine for Resolve_Hub.
Performs efficient ORM aggregations to analyze actual complaint records by
institution, category, priority, status, and time velocity.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from django.db.models import Avg, Case, Count, DurationField, ExpressionWrapper, F, Q, Value, When
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.complaints.models import Complaint, ComplaintCategory, PriorityLevel, Status
from apps.institutions.models import Institution


def compute_institutional_analytics(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Computes institutional complaint trends, rankings, and distribution metrics.
    Uses purely database-level aggregations to ensure performance and data integrity.
    """
    filters = params or {}
    now = timezone.now()

    # Base QuerySet
    qs = Complaint.objects.select_related("institution", "category")

    # 1. Apply User Filters
    # Date filtering
    date_from_str = filters.get("date_from", "").strip()
    date_to_str = filters.get("date_to", "").strip()
    date_from = parse_date(date_from_str) if date_from_str else None
    date_to = parse_date(date_to_str) if date_to_str else None

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    # Institution filter
    inst_val = filters.get("institution", "").strip()
    if inst_val:
        if inst_val.isdigit():
            qs = qs.filter(institution_id=int(inst_val))
        else:
            qs = qs.filter(
                Q(institution__name__icontains=inst_val)
                | Q(institution__aicte_id__icontains=inst_val)
            )

    # Category filter
    cat_val = filters.get("category", "").strip()
    if cat_val:
        if cat_val.isdigit():
            qs = qs.filter(category_id=int(cat_val))
        else:
            qs = qs.filter(category__slug=cat_val)

    # Priority filter
    priority_val = filters.get("priority", "").strip()
    if priority_val in dict(PriorityLevel.choices):
        qs = qs.filter(priority=priority_val)

    # Status filter
    status_val = filters.get("status", "").strip()
    if status_val in dict(Status.choices):
        qs = qs.filter(status=status_val)

    # State filter
    state_val = filters.get("state", "").strip()
    if state_val:
        qs = qs.filter(institution__state__iexact=state_val)

    # 2. Key Performance Indicators (KPIs)
    total_complaints = qs.count()

    critical_count = qs.filter(priority=PriorityLevel.CRITICAL).count()
    high_count = qs.filter(priority=PriorityLevel.HIGH).count()
    critical_high_count = critical_count + high_count

    pending_statuses = [
        Status.SUBMITTED,
        Status.UNDER_REVIEW,
        Status.IN_PROGRESS,
        Status.AWAITING_COMPLAINANT,
    ]
    pending_count = qs.filter(status__in=pending_statuses).count()

    overdue_count = qs.filter(
        status__in=pending_statuses,
        sla_due_at__isnull=False,
        sla_due_at__lt=now,
    ).count()

    resolved_count = qs.filter(status=Status.RESOLVED).count()

    # Average resolution time
    resolved_qs = qs.filter(resolved_at__isnull=False).annotate(
        resolution_time=ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())
    )
    avg_resolution = resolved_qs.aggregate(avg=Avg("resolution_time"))["avg"]
    avg_resolution_hours = round(avg_resolution.total_seconds() / 3600, 1) if avg_resolution else None

    # 3. Institutional Rankings & Breakdown
    inst_grouped = (
        qs.filter(institution__isnull=False)
        .values(
            "institution__id",
            "institution__name",
            "institution__aicte_id",
            "institution__state",
        )
        .annotate(
            total_count=Count("id"),
            critical_high_count=Count(
                "id",
                filter=Q(priority__in=[PriorityLevel.CRITICAL, PriorityLevel.HIGH]),
            ),
            pending_count=Count("id", filter=Q(status__in=pending_statuses)),
            overdue_count=Count(
                "id",
                filter=Q(
                    status__in=pending_statuses,
                    sla_due_at__isnull=False,
                    sla_due_at__lt=now,
                ),
            ),
            resolved_count=Count("id", filter=Q(status=Status.RESOLVED)),
        )
        .order_by("-total_count", "-critical_high_count", "institution__name")
    )

    institution_rankings = list(inst_grouped)

    # Threshold for frequent or unusually high volume
    total_inst_with_complaints = len(institution_rankings)
    mean_volume = (
        (sum(i["total_count"] for i in institution_rankings) / total_inst_with_complaints)
        if total_inst_with_complaints > 0
        else 0
    )
    high_volume_threshold = max(3, round(mean_volume * 1.5, 1))

    frequent_institutions_count = 0
    for inst in institution_rankings:
        is_high_volume = inst["total_count"] >= high_volume_threshold
        inst["is_high_volume"] = is_high_volume
        if is_high_volume:
            frequent_institutions_count += 1

    # 4. Repeated Complaint Categories per Institution
    repeated_categories_qs = (
        qs.filter(institution__isnull=False, category__isnull=False)
        .values("institution__id", "institution__name", "category__name")
        .annotate(cat_count=Count("id"))
        .filter(cat_count__gte=2)
        .order_by("-cat_count", "institution__name")[:25]
    )
    repeated_categories = list(repeated_categories_qs)

    # 5. Volume Velocity: Institutions with increasing volumes over time
    # Compare recent 30-day window vs prior 30-day window
    recent_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)

    recent_counts = dict(
        qs.filter(institution__isnull=False, created_at__gte=recent_start)
        .values("institution__id")
        .annotate(cnt=Count("id"))
        .values_list("institution__id", "cnt")
    )
    prior_counts = dict(
        qs.filter(
            institution__isnull=False,
            created_at__gte=prior_start,
            created_at__lt=recent_start,
        )
        .values("institution__id")
        .annotate(cnt=Count("id"))
        .values_list("institution__id", "cnt")
    )

    velocity_institutions: List[Dict[str, Any]] = []
    for inst in institution_rankings:
        iid = inst["institution__id"]
        rec = recent_counts.get(iid, 0)
        pri = prior_counts.get(iid, 0)
        # Identify institutions whose volume is climbing
        if rec > pri and rec >= 2:
            increase = rec - pri
            growth_pct = round(((rec - pri) / max(1, pri)) * 100)
            velocity_institutions.append({
                "institution_id": iid,
                "institution_name": inst["institution__name"],
                "aicte_id": inst["institution__aicte_id"],
                "recent_count": rec,
                "prior_count": pri,
                "increase": increase,
                "growth_pct": growth_pct,
            })
    velocity_institutions.sort(key=lambda x: (x["increase"], x["recent_count"]), reverse=True)

    # 6. Priority & Status Distributions
    priority_counts = list(
        qs.values("priority")
        .annotate(count=Count("id"))
        .order_by("priority")
    )
    status_counts = list(
        qs.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    category_counts = list(
        qs.filter(category__isnull=False)
        .values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # 7. Time Trend Data (Monthly or Weekly)
    # Check date span to choose appropriate grouping granularity
    earliest_date = qs.order_by("created_at").values_list("created_at", flat=True).first()
    use_weekly = False
    if earliest_date and (now - earliest_date).days <= 60:
        use_weekly = True

    if use_weekly:
        trend_qs = (
            qs.annotate(period=TruncWeek("created_at"))
            .values("period")
            .annotate(
                total=Count("id"),
                critical_high=Count(
                    "id", filter=Q(priority__in=[PriorityLevel.CRITICAL, PriorityLevel.HIGH])
                ),
                resolved=Count("id", filter=Q(status=Status.RESOLVED)),
            )
            .order_by("period")
        )
        date_format = "%d %b %Y"
    else:
        trend_qs = (
            qs.annotate(period=TruncMonth("created_at"))
            .values("period")
            .annotate(
                total=Count("id"),
                critical_high=Count(
                    "id", filter=Q(priority__in=[PriorityLevel.CRITICAL, PriorityLevel.HIGH])
                ),
                resolved=Count("id", filter=Q(status=Status.RESOLVED)),
            )
            .order_by("period")
        )
        date_format = "%b %Y"

    trend_labels = []
    trend_totals = []
    trend_critical_highs = []
    trend_resolveds = []
    for item in trend_qs:
        period_dt = item["period"]
        if period_dt:
            trend_labels.append(period_dt.strftime(date_format))
            trend_totals.append(item["total"])
            trend_critical_highs.append(item["critical_high"])
            trend_resolveds.append(item["resolved"])

    # 8. Issues needing immediate administrative attention
    attention_issues = []
    for inst in institution_rankings:
        reasons = []
        if inst["overdue_count"] > 0:
            reasons.append(f"{inst['overdue_count']} SLA overdue complaints")
        if inst["critical_high_count"] >= 3:
            reasons.append(f"{inst['critical_high_count']} Critical/High priority complaints")
        if inst["is_high_volume"]:
            reasons.append(f"Unusually high complaint volume ({inst['total_count']} total)")

        if reasons:
            attention_issues.append({
                "institution_id": inst["institution__id"],
                "institution_name": inst["institution__name"],
                "aicte_id": inst["institution__aicte_id"],
                "state": inst["institution__state"],
                "total_count": inst["total_count"],
                "reasons": reasons,
            })
    attention_issues = attention_issues[:10]

    # Available options for filter dropdowns
    all_institutions = list(
        Institution.objects.filter(is_active=True).values("id", "name", "aicte_id")[:200]
    )
    all_categories = list(ComplaintCategory.objects.filter(is_active=True).values("id", "name", "slug"))
    all_states = list(
        Institution.objects.filter(is_active=True)
        .values_list("state", flat=True)
        .distinct()
        .order_by("state")
    )

    return {
        "kpis": {
            "total_complaints": total_complaints,
            "critical_high_count": critical_high_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "resolved_count": resolved_count,
            "frequent_institutions_count": frequent_institutions_count,
            "avg_resolution_hours": avg_resolution_hours,
            "high_volume_threshold": high_volume_threshold,
        },
        "institution_rankings": institution_rankings,
        "repeated_categories": repeated_categories,
        "velocity_institutions": velocity_institutions,
        "attention_issues": attention_issues,
        "priority_counts": priority_counts,
        "status_counts": status_counts,
        "category_counts": category_counts,
        "trend_chart": {
            "labels": trend_labels,
            "totals": trend_totals,
            "critical_highs": trend_critical_highs,
            "resolveds": trend_resolveds,
        },
        "filter_options": {
            "institutions": all_institutions,
            "categories": all_categories,
            "states": all_states,
            "priorities": PriorityLevel.choices,
            "statuses": Status.choices,
        },
        "applied_filters": {
            "date_from": date_from_str,
            "date_to": date_to_str,
            "institution": inst_val,
            "category": cat_val,
            "priority": priority_val,
            "status": status_val,
            "state": state_val,
        },
    }

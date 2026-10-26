from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from django.conf import settings
from django.utils import timezone

from .models import Institution, InstitutionRiskScore, RiskBand

if TYPE_CHECKING:
    pass


def compute_risk(institution: Institution) -> InstitutionRiskScore:
    """
    Compute explainable risk score for an institution (0 to 100) based on:
      1. Complaint volume in last 12 months (weight 20%)
      2. High/Critical priority share (weight 25%)
      3. Repeat complaint / duplicate rate (weight 20%)
      4. SLA breached / unresolved share (weight 20%)
      5. Court / RTI matters count (weight 15%)
    
    All signals are clamped to [0, 100]. Output NEVER contains complainant PII.
    """
    now = timezone.now()
    one_year_ago = now - timedelta(days=365)

    from apps.complaints.models import Complaint, PriorityLevel, Status

    complaints_qs = Complaint.objects.filter(institution=institution)
    recent_qs = complaints_qs.filter(created_at__gte=one_year_ago)

    total_recent = recent_qs.count()

    # 1. Volume score (0-100): 10 complaints in a year = 100
    volume_score = min(100.0, (total_recent / 10.0) * 100.0) if total_recent > 0 else 0.0

    # 2. High / Critical share (0-100)
    high_crit_count = recent_qs.filter(priority__in=[PriorityLevel.HIGH, PriorityLevel.CRITICAL]).count()
    severity_score = (high_crit_count / total_recent * 100.0) if total_recent > 0 else 0.0

    # 3. Repeat complaint / duplicate rate (0-100)
    duplicate_count = recent_qs.filter(duplicate_of__isnull=False).count()
    # Check if multiple complaints share same category
    category_counts = recent_qs.values("category").count()
    distinct_categories = recent_qs.values("category").distinct().count()
    repeat_category_penalty = max(0, category_counts - distinct_categories) * 15.0
    repeat_score = min(100.0, ((duplicate_count * 30.0) + repeat_category_penalty)) if total_recent > 0 else 0.0

    # 4. Unresolved / SLA breached share (0-100)
    # SLA breached count or escalated count
    breached_count = recent_qs.filter(
        status__in=[Status.SUBMITTED, Status.UNDER_REVIEW, Status.IN_PROGRESS, "AWAITING_COMPLAINANT"],
        sla_due_at__isnull=False,
        sla_due_at__lt=now,
    ).count()
    unresolved_count = recent_qs.exclude(status__in=[Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]).count()
    sla_score = min(100.0, ((breached_count * 40.0) + (unresolved_count / max(1, total_recent) * 60.0))) if total_recent > 0 else 0.0

    # 5. Court / RTI matters count (0-100)
    court_rti_count = recent_qs.filter(is_court_rti=True).count()
    court_score = min(100.0, court_rti_count * 50.0)

    # Weighted calculation
    weight_vol = getattr(settings, "RISK_WEIGHT_VOLUME", 0.20)
    weight_sev = getattr(settings, "RISK_WEIGHT_SEVERITY", 0.25)
    weight_rep = getattr(settings, "RISK_WEIGHT_REPEAT", 0.20)
    weight_sla = getattr(settings, "RISK_WEIGHT_SLA", 0.20)
    weight_crt = getattr(settings, "RISK_WEIGHT_COURT", 0.15)

    final_score = (
        (volume_score * weight_vol)
        + (severity_score * weight_sev)
        + (repeat_score * weight_rep)
        + (sla_score * weight_sla)
        + (court_score * weight_crt)
    )
    final_score = round(max(0.0, min(100.0, final_score)), 1)

    if final_score >= 80.0:
        band = RiskBand.CRITICAL
    elif final_score >= 60.0:
        band = RiskBand.HIGH
    elif final_score >= 30.0:
        band = RiskBand.MEDIUM
    else:
        band = RiskBand.LOW

    components = {
        "volume_score": round(volume_score, 1),
        "severity_score": round(severity_score, 1),
        "repeat_score": round(repeat_score, 1),
        "sla_score": round(sla_score, 1),
        "court_score": round(court_score, 1),
        "total_complaints_12m": total_recent,
        "high_priority_count": high_crit_count,
        "duplicate_count": duplicate_count,
        "court_rti_count": court_rti_count,
    }

    risk_record, _ = InstitutionRiskScore.objects.update_or_create(
        institution=institution,
        defaults={
            "score": final_score,
            "band": band,
            "components": components,
            "computed_at": now,
        },
    )
    return risk_record

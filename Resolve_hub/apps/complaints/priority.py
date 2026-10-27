"""
Intelligent Complaint Prioritisation Engine for Resolve_Hub.
Deterministic, explainable, lightweight pure-Python scoring module.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from django.utils import timezone


# ---------------------------------------------------------------------------
# Priority Levels & Thresholds
# ---------------------------------------------------------------------------
class PriorityLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Centralized Priority Thresholds (Score range: 0 - 100)
THRESHOLD_CRITICAL = 70
THRESHOLD_HIGH = 45
THRESHOLD_MEDIUM = 20

# Centralized Scoring Weights / Points
POINTS_COURT_RTI = 40
POINTS_CRITICAL_KEYWORD = 45
POINTS_HIGH_KEYWORD = 35
POINTS_STUDENT_URGENCY_HIGH = 20
POINTS_STUDENT_URGENCY_MED = 10
POINTS_ESCALATION_PER_LEVEL = 15
POINTS_SLA_BREACH = 25
POINTS_SLA_NEAR_BREACH = 10

# Age points for unresolved complaints only
POINTS_AGE_OVER_30_DAYS = 25
POINTS_AGE_OVER_14_DAYS = 15
POINTS_AGE_OVER_7_DAYS = 8

# Recurring complaint points (same institution + category)
POINTS_RECURRING_HIGH = 25    # >= 5 occurrences
POINTS_RECURRING_MED = 15     # >= 3 occurrences
POINTS_RECURRING_LOW = 8      # >= 2 occurrences

# Centralized Safety & Harassment Keywords
CRITICAL_KEYWORDS = (
    "ragging", "suicide", "sexual harassment", "assault", "violence",
    "threat to life", "death threat", "physical abuse", "molestation",
    "रैगिंग", "आत्महत्या", "यौन उत्पीड़न", "हमला", "हिंसा", "जान से मारने की धमकी",
)

HIGH_KEYWORDS = (
    "fraud", "fake approval", "unapproved", "extortion", "blackmail",
    "bribe", "capitation fee", "safety hazard", "electric shock", "fire",
    "harassment", "caste discrimination", "sc/st",
    "धोखाधड़ी", "फर्जी मान्यता", "ब्लैकमेल", "रिश्वत", "डोनेशन", "सुरक्षा खतरा", "आग",
)

CLOSED_STATUSES = frozenset({"RESOLVED", "CLOSED", "REJECTED", "SPAM"})


def _extract_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """Safely extracts field from model instance, dict, or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def compute_priority(
    complaint: Any,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, int, List[str]]:
    """
    Computes priority level, numeric score (0-100), and explainable reasons.

    Args:
        complaint: Complaint model instance or dict-like object.
        context: Optional precalculated metrics (e.g. recurring_count, now_datetime).

    Returns:
        (level, score, reasons)
        level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
        score: integer between 0 and 100
        reasons: list of short explanation strings
    """
    score = 0
    reasons: List[str] = []
    ctx = context or {}

    now = ctx.get("now")
    if not isinstance(now, datetime):
        now = timezone.now()

    # 1. Court / RTI matters check
    is_court_rti = bool(_extract_field(complaint, "is_court_rti", False))
    if is_court_rti:
        score += POINTS_COURT_RTI
        reasons.append("Court or RTI referral requires expedited oversight (+40)")

    # 2. Text keyword analysis (subject & description)
    subject = str(_extract_field(complaint, "subject", "") or "")
    description = str(_extract_field(complaint, "description", "") or "")
    combined_text = f"{subject} {description}".lower()

    found_critical_kw = [kw for kw in CRITICAL_KEYWORDS if kw in combined_text]
    if found_critical_kw:
        score += POINTS_CRITICAL_KEYWORD
        matched_str = ", ".join(f"'{kw}'" for kw in found_critical_kw[:2])
        reasons.append(f"Critical safety/harassment indicator detected: {matched_str} (+45)")

    found_high_kw = [kw for kw in HIGH_KEYWORDS if kw in combined_text]
    if found_high_kw and not found_critical_kw:
        score += POINTS_HIGH_KEYWORD
        matched_str = ", ".join(f"'{kw}'" for kw in found_high_kw[:2])
        reasons.append(f"High-severity compliance or hazard indicator: {matched_str} (+25)")

    # 3. Category safety indicators
    category_obj = _extract_field(complaint, "category", None)
    category_name = ""
    if category_obj:
        category_name = str(_extract_field(category_obj, "name", "") or "")
    if not category_name:
        category_name = str(_extract_field(complaint, "category_name", "") or "")

    cat_lower = category_name.lower()
    if any(k in cat_lower for k in ("ragging", "harassment", "safety", "women", "sc/st")):
        score += 15
        reasons.append(f"High-risk category '{category_name}' (+15)")

    # 4. Student Urgency
    student_urgency = str(_extract_field(complaint, "student_urgency", "MEDIUM") or "").upper()
    if student_urgency == "HIGH":
        score += POINTS_STUDENT_URGENCY_HIGH
        reasons.append("High urgency reported by complainant (+20)")
    elif student_urgency == "MEDIUM":
        score += POINTS_STUDENT_URGENCY_MED

    # 5. Escalation level
    escalation_level = int(_extract_field(complaint, "escalation_level", 0) or 0)
    if escalation_level > 0:
        esc_points = min(30, escalation_level * POINTS_ESCALATION_PER_LEVEL)
        score += esc_points
        reasons.append(f"Administrative escalation level L{escalation_level} (+{esc_points})")

    # 6. Status and Age / SLA handling
    # Resolved or closed complaints must NOT be escalated solely because of age or SLA
    status = str(_extract_field(complaint, "status", "SUBMITTED") or "").upper()
    is_closed = status in CLOSED_STATUSES

    if not is_closed:
        # Check SLA breach / overdue
        sla_due_at = _extract_field(complaint, "sla_due_at", None)
        is_sla_breached = bool(_extract_field(complaint, "is_sla_breached", False))
        if sla_due_at and hasattr(sla_due_at, "__lt__"):
            try:
                if sla_due_at < now:
                    is_sla_breached = True
            except TypeError:
                pass

        if is_sla_breached:
            score += POINTS_SLA_BREACH
            reasons.append("SLA deadline exceeded on active grievance (+25)")
        elif sla_due_at and hasattr(sla_due_at, "__sub__"):
            try:
                time_left = sla_due_at - now
                if timedelta(0) <= time_left <= timedelta(hours=24):
                    score += POINTS_SLA_NEAR_BREACH
                    reasons.append("SLA deadline approaching within 24 hours (+10)")
            except TypeError:
                pass

        # Days unresolved
        created_at = _extract_field(complaint, "created_at", None)
        if created_at and hasattr(now, "__sub__"):
            try:
                days_open = (now - created_at).days
                if days_open >= 30:
                    score += POINTS_AGE_OVER_30_DAYS
                    reasons.append(f"Unresolved for {days_open} days (+25)")
                elif days_open >= 14:
                    score += POINTS_AGE_OVER_14_DAYS
                    reasons.append(f"Unresolved for {days_open} days (+15)")
                elif days_open >= 7:
                    score += POINTS_AGE_OVER_7_DAYS
                    reasons.append(f"Unresolved for {days_open} days (+8)")
            except (TypeError, AttributeError):
                pass
    else:
        reasons.append(f"Complaint status is {status}; age/overdue escalation suppressed")

    # 7. Recurring complaints for same institution and category
    recurring_count = ctx.get("recurring_count")
    if recurring_count is None:
        inst_id = _extract_field(complaint, "institution_id", None)
        if not inst_id:
            inst = _extract_field(complaint, "institution", None)
            inst_id = _extract_field(inst, "id", None)

        cat_id = _extract_field(complaint, "category_id", None)
        if not cat_id and category_obj:
            cat_id = _extract_field(category_obj, "id", None)

        # Optional batched dict check: ctx["recurring_map"] = {(inst_id, cat_id): count}
        recurring_map = ctx.get("recurring_map")
        if recurring_map and (inst_id, cat_id) in recurring_map:
            recurring_count = recurring_map[(inst_id, cat_id)]

    if recurring_count and recurring_count >= 5:
        score += POINTS_RECURRING_HIGH
        reasons.append(f"Recurring pattern: {recurring_count} similar complaints in institution (+25)")
    elif recurring_count and recurring_count >= 3:
        score += POINTS_RECURRING_MED
        reasons.append(f"Repeated issue: {recurring_count} similar complaints in institution (+15)")
    elif recurring_count and recurring_count >= 2:
        score += POINTS_RECURRING_LOW
        reasons.append(f"Institutional repeat: {recurring_count} complaints in same category (+8)")

    # Normalize score
    clamped_score = max(0, min(100, score))

    # Priority level assignment
    if clamped_score >= THRESHOLD_CRITICAL:
        level = PriorityLevel.CRITICAL
    elif clamped_score >= THRESHOLD_HIGH:
        level = PriorityLevel.HIGH
    elif clamped_score >= THRESHOLD_MEDIUM:
        level = PriorityLevel.MEDIUM
    else:
        level = PriorityLevel.LOW

    if not reasons:
        reasons.append("Standard grievance within normal operating parameters")

    return level, clamped_score, reasons


def get_complaint_priority_summary(complaint: Any, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns a single-line explainable reason summary for display in listings and headers.
    """
    _, score, reasons = compute_priority(complaint, context)
    primary_reasons = [r for r in reasons if "(+" in r]
    if primary_reasons:
        lead = "; ".join(primary_reasons[:2])
        return f"{lead} (Score: {score}/100)"
    return f"{reasons[0]} (Score: {score}/100)"


def get_priority_badge_class(priority: str) -> str:
    """
    Returns appropriate Bootstrap badge class matching existing Resolve_Hub styles.
    """
    pri = (priority or "").upper()
    if pri == "CRITICAL":
        return "bg-danger text-white"
    if pri == "HIGH":
        return "bg-warning text-dark"
    if pri == "MEDIUM":
        return "bg-info text-dark"
    return "bg-secondary text-white"

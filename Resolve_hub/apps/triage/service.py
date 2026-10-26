from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional

from django.conf import settings
from django.utils import timezone

from apps.complaints.models import Complaint, ComplaintCategory, PriorityLevel
from apps.institutions.models import Cell, Institution
from .classifier import detect_language, predict_category


@dataclass
class TriageResult:
    category: ComplaintCategory
    priority: str
    cell: Optional[Cell]
    language: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    duplicate_candidate: Optional[Complaint] = None
    triage_needs_review: bool = False


# High severity keywords
CRITICAL_KEYWORDS = [
    "ragging", "suicide", "sexual harassment", "assault", "violence", "threat to life",
    "रैगिंग", "आत्महत्या", "यौन उत्पीड़न", "हमला", "हिंसा", "जान से मारने की धमकी",
]

HIGH_KEYWORDS = [
    "fraud", "fake approval", "unapproved", "extortion", "blackmail", "bribe", "capitation fee",
    "safety hazard", "electric shock", "fire",
    "धोखाधड़ी", "फर्जी मान्यता", "ब्लैकमेल", "रिश्वत", "डोनेशन", "सुरक्षा खतरा", "आग",
]


def _check_priority_rules(
    full_text: str,
    institution: Optional[Institution],
    is_court_rti: bool,
) -> tuple[str, list[str]]:
    reasons = []
    text_lower = full_text.lower()

    if is_court_rti:
        reasons.append("Court or RTI referral requires high priority handling.")
        return PriorityLevel.CRITICAL, reasons

    # 1. Critical keywords
    for kw in CRITICAL_KEYWORDS:
        if kw in text_lower:
            reasons.append(f"Contains critical safety/harassment indicator: '{kw}'.")
            return PriorityLevel.CRITICAL, reasons

    # 2. High keywords
    for kw in HIGH_KEYWORDS:
        if kw in text_lower:
            reasons.append(f"Contains high severity compliance/fraud indicator: '{kw}'.")
            return PriorityLevel.HIGH, reasons

    # 3. Repeated complaints against same institution check
    base_priority = PriorityLevel.MEDIUM
    if institution:
        recent_count = Complaint.objects.filter(
            institution=institution,
            created_at__gte=timezone.now() - timedelta(days=60),
        ).count()
        if recent_count >= 5:
            reasons.append(f"Elevated priority: Institution has {recent_count} complaints in last 60 days.")
            base_priority = PriorityLevel.HIGH

    reasons.append("Assigned standard priority based on text signals.")
    return base_priority, reasons


def _find_institution_duplicate(
    institution: Institution,
    full_text: str,
) -> Optional[Complaint]:
    """
    Cross-complainant duplicate detection scoped to the SAME institution:
    TF-IDF cosine similarity against open complaints in the last 90 days.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    cutoff = timezone.now() - timedelta(days=90)
    open_complaints = list(
        Complaint.objects.filter(
            institution=institution,
            created_at__gte=cutoff,
        )
        .exclude(status__in=["RESOLVED", "CLOSED", "REJECTED", "SPAM"])
        .order_by("created_at")[:50]
    )

    if not open_complaints:
        return None

    corpus = [f"{c.subject} {c.description}" for c in open_complaints]
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        matrix = vectorizer.fit_transform([full_text] + corpus)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()

        threshold = getattr(settings, "DUPLICATE_LINK_THRESHOLD", 0.80)
        best_idx = int(similarities.argmax())
        best_score = float(similarities[best_idx])

        if best_score >= threshold:
            return open_complaints[best_idx]
    except Exception:
        pass

    return None


def triage_complaint(
    subject: str,
    description: str,
    institution: Optional[Institution] = None,
    is_court_rti: bool = False,
) -> TriageResult:
    """
    Pure-Python, unit-testable service that triages a grievance:
    determines language, ML category prediction, cell routing,
    priority scoring with reasons, and duplicate linking.
    """
    full_text = f"{subject} {description}".strip()
    language = detect_language(full_text)

    # 1. Category Classification
    predicted_cat_name, confidence = predict_category(full_text)
    threshold = getattr(settings, "TRIAGE_CONFIDENCE_THRESHOLD", 0.45)
    triage_needs_review = confidence < threshold

    # Match ComplaintCategory model
    category = ComplaintCategory.objects.filter(name__iexact=predicted_cat_name).first()
    if not category:
        category = ComplaintCategory.objects.filter(is_active=True).first()
        if not category:
            category = ComplaintCategory.objects.create(name="Other", slug="other")

    # 2. Priority Determination
    priority, reasons = _check_priority_rules(full_text, institution, is_court_rti)
    reasons.append(f"Predicted category '{category.name}' with {int(confidence * 100)}% confidence.")

    # 3. Cell Routing
    cell = None
    if is_court_rti:
        cell = Cell.objects.filter(slug__in=["legal", "legal-bureau"]).first()
        reasons.append("Routed to Legal cell due to Court/RTI flag.")

    if not cell:
        # Check configured CategoryCellRoute
        from apps.complaints.models import CategoryCellRoute
        route = CategoryCellRoute.objects.filter(category=category).select_related("cell").first()
        if route:
            cell = route.cell
            reasons.append(f"Routed to '{cell.name}' via category route policy.")

    if not cell:
        cat_lower = category.name.lower()
        if "approval" in cat_lower or "affiliation" in cat_lower:
            cell = Cell.objects.filter(slug="approval").first()
        elif "regional" in cat_lower or "transport" in cat_lower:
            cell = Cell.objects.filter(slug="regional-office").first()
        elif "legal" in cat_lower:
            cell = Cell.objects.filter(slug="legal").first()
        else:
            cell = Cell.objects.filter(slug="pgrc").first()

        if cell:
            reasons.append(f"Routed to default cell '{cell.name}'.")

    # 4. Cross-complainant duplicate linking (same institution)
    duplicate_candidate = None
    if institution:
        duplicate_candidate = _find_institution_duplicate(institution, full_text)
        if duplicate_candidate:
            reasons.append(f"Linked as potential duplicate of earlier case {duplicate_candidate.complaint_code}.")

    return TriageResult(
        category=category,
        priority=priority,
        cell=cell,
        language=language,
        confidence=confidence,
        reasons=reasons,
        duplicate_candidate=duplicate_candidate,
        triage_needs_review=triage_needs_review,
    )

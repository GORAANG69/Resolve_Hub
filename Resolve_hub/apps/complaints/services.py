"""
Centralized complaint status transition and intake service for Resolve_Hub.
All complaint creation MUST go through register_complaint(...).
All status transitions MUST go through change_complaint_status(...).
"""
from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Optional, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.institutions.models import Cell, Institution
from apps.institutions.services import resolve_sla_hours
from apps.triage.service import triage_complaint

from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintStatusHistory,
    PriorityLevel,
    SourceChannel,
    Status,
    _generate_complaint_code,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    Status.SUBMITTED: {Status.UNDER_REVIEW, Status.REJECTED, Status.SPAM, Status.AWAITING_COMPLAINANT},
    Status.UNDER_REVIEW: {Status.IN_PROGRESS, Status.REJECTED, Status.SPAM, Status.AWAITING_COMPLAINANT},
    Status.IN_PROGRESS: {Status.RESOLVED, Status.UNDER_REVIEW, Status.AWAITING_COMPLAINANT, Status.REJECTED},
    Status.AWAITING_COMPLAINANT: {Status.UNDER_REVIEW, Status.IN_PROGRESS, Status.RESOLVED, Status.CLOSED},
    Status.RESOLVED: {Status.CLOSED, Status.IN_PROGRESS},
    Status.REJECTED: set(),
    Status.SPAM: set(),
    Status.CLOSED: set(),
}


def compute_contact_hash(contact: str) -> str:
    """Deterministic salted hash of complainant email or mobile for privacy-safe tracker lookups."""
    if not contact:
        return ""
    clean = contact.strip().lower()
    return hashlib.sha256(f"{settings.SECRET_KEY}:{clean}".encode("utf-8")).hexdigest()


def get_system_intake_user():
    """Retrieve or create system account for external channels (Email, CPGRAMS, OCR)."""
    User = get_user_model()
    email = "system-intake@resolvehub.local"
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "full_name": "Resolve_Hub Automated Intake",
            "role": "STUDENT",
            "is_active": True,
        },
    )
    return user


@transaction.atomic
def register_complaint(
    *,
    submitting_user,
    institution: Union[Institution, str, int, None],
    subject: str,
    description: str,
    category: Optional[ComplaintCategory] = None,
    department_or_location: str = "",
    student_urgency: str = "MEDIUM",
    source_channel: str = SourceChannel.WEB,
    is_court_rti: bool = False,
    court_rti_reference: str = "",
    external_reference: str = "",
    is_confidential: bool = False,
    consent_given: bool = True,
    language: Optional[str] = None,
) -> Complaint:
    """
    The canonical intake service for Resolve_Hub across all channels:
    Validates institution, assigns submitting user, triages matter,
    computes SLA, performs spam scoring, writes status history and audit log.
    Never trusts client-supplied owner, status, priority, cell or SLA.
    """
    if not submitting_user:
        submitting_user = get_system_intake_user()

    # 1. Resolve institution
    resolved_institution = None
    if isinstance(institution, Institution):
        resolved_institution = institution
    elif isinstance(institution, int):
        resolved_institution = Institution.objects.filter(pk=institution).first()
    elif isinstance(institution, str) and institution.strip():
        # Match by aicte_id or name or pk
        resolved_institution = (
            Institution.objects.filter(aicte_id=institution.strip()).first()
            or Institution.objects.filter(name__icontains=institution.strip()).first()
        )
        if not resolved_institution and institution.isdigit():
            resolved_institution = Institution.objects.filter(pk=int(institution)).first()

    # 2. Run AI Triage
    triage_res = triage_complaint(
        subject=subject,
        description=description,
        institution=resolved_institution,
        is_court_rti=is_court_rti,
    )

    resolved_category = category or triage_res.category
    resolved_cell = triage_res.cell
    resolved_priority = triage_res.priority
    detected_language = language or triage_res.language

    # 3. Compute SLA Due At
    sla_hours = resolve_sla_hours(resolved_cell, resolved_category, resolved_priority)
    now = timezone.now()
    sla_due_at = now + timedelta(hours=sla_hours)

    # 4. Contact hash for public tracker lookup
    contact_str = getattr(submitting_user, "email", "") or getattr(submitting_user, "mobile_number", "")
    contact_hash = compute_contact_hash(contact_str)

    complaint = Complaint.objects.create(
        complaint_code=_generate_complaint_code(),
        student=submitting_user,
        category=resolved_category,
        institution=resolved_institution,
        cell=resolved_cell,
        subject=subject,
        description=description,
        department_or_location=department_or_location,
        student_urgency=student_urgency,
        source_channel=source_channel,
        language=detected_language,
        priority=resolved_priority,
        triage_confidence=triage_res.confidence,
        triage_needs_review=triage_res.triage_needs_review or (resolved_institution is None),
        sla_due_at=sla_due_at,
        is_court_rti=is_court_rti,
        court_rti_reference=court_rti_reference,
        external_reference=external_reference,
        duplicate_of=triage_res.duplicate_candidate,
        is_confidential=is_confidential,
        consent_given_at=now if consent_given else None,
        consent_version="1.0" if consent_given else "",
        complainant_contact_hash=contact_hash,
        status=Status.SUBMITTED,
    )

    # 5. Run spam analysis
    from apps.spam_detection.services import run_and_save_spam_analysis
    run_and_save_spam_analysis(complaint)

    # 6. Status History & Audit Log
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status="",
        new_status=Status.SUBMITTED,
        changed_by=submitting_user,
        remark=f"Grievance logged via {source_channel}.",
    )

    log_action(
        actor=submitting_user,
        action="COMPLAINT_REGISTERED",
        target=f"complaint:{complaint.pk}",
        metadata={
            "channel": source_channel,
            "institution": resolved_institution.name if resolved_institution else None,
            "cell": resolved_cell.name if resolved_cell else None,
            "priority": resolved_priority,
            "is_court_rti": is_court_rti,
        },
    )

    return complaint


# Backwards-compatible wrapper
def create_complaint(*, student, category, subject: str, description: str,
                     department_or_location: str = "", student_urgency: str = "MEDIUM",
                     is_confidential: bool = False, institution=None) -> Complaint:
    return register_complaint(
        submitting_user=student,
        institution=institution,
        category=category,
        subject=subject,
        description=description,
        department_or_location=department_or_location,
        student_urgency=student_urgency,
        is_confidential=is_confidential,
        source_channel=SourceChannel.WEB,
        consent_given=True,
    )


@transaction.atomic
def change_complaint_status(*, complaint: Complaint, new_status: str, actor, remark: str = "") -> Complaint:
    old_status = complaint.status

    if new_status not in dict(Status.choices):
        raise ValidationError(f"Unknown status: {new_status}")

    if new_status == old_status:
        raise ValidationError("Complaint is already in that status.")

    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ValidationError(f"Cannot move complaint from {old_status} to {new_status}.")

    complaint.status = new_status
    now = timezone.now()

    # SLA Pause semantics:
    # If entering AWAITING_COMPLAINANT, pause the SLA clock
    if new_status == Status.AWAITING_COMPLAINANT:
        complaint.sla_paused_at = now
    # If leaving AWAITING_COMPLAINANT, unpause and extend sla_due_at
    elif old_status == Status.AWAITING_COMPLAINANT and complaint.sla_paused_at:
        paused_duration = now - complaint.sla_paused_at
        complaint.sla_paused_total += paused_duration
        if complaint.sla_due_at:
            complaint.sla_due_at += paused_duration
        complaint.sla_paused_at = None

    if new_status == Status.RESOLVED:
        complaint.resolved_at = now
    elif old_status == Status.RESOLVED and new_status == Status.IN_PROGRESS:
        complaint.resolved_at = None

    complaint.save(update_fields=["status", "resolved_at", "updated_at", "sla_paused_at", "sla_paused_total", "sla_due_at"])

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=old_status,
        new_status=new_status,
        changed_by=actor,
        remark=remark,
    )

    log_action(
        actor=actor,
        action="COMPLAINT_STATUS_CHANGED",
        target=f"complaint:{complaint.pk}",
        metadata={"old_status": old_status, "new_status": new_status, "remark": remark},
    )

    return complaint


@transaction.atomic
def forward_complaint_to_department(*, complaint: Complaint, department: str, actor) -> Complaint:
    complaint.assigned_department = department
    complaint.assigned_at = timezone.now()
    complaint.assigned_by = actor
    complaint.save(update_fields=["assigned_department", "assigned_at", "assigned_by"])

    log_action(
        actor=actor,
        action="COMPLAINT_FORWARDED_TO_HOD",
        target=f"complaint:{complaint.pk}",
        metadata={"department": department},
    )
    return complaint

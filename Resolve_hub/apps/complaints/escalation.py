from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.audit.services import log_action
from apps.complaints.models import Complaint, EscalationEvent, Status

logger = logging.getLogger(__name__)


def _send_escalation_notification(
    complaint: Complaint,
    level: int,
    recipient: Optional[User],
) -> str:
    """
    Deliver escalation notification to responsible officer.
    STRICT SECURITY RULE: Notification text must NOT contain complainant PII,
    only case ID, institution, cell, escalation level, and SLA due time.
    """
    inst_name = complaint.institution.name if complaint.institution else "General"
    cell_name = complaint.cell.name if complaint.cell else "Unassigned"
    due_str = complaint.sla_due_at.strftime("%d %b %Y %H:%M UTC") if complaint.sla_due_at else "Unspecified"

    subject = f"[Resolve_Hub Alert] Case {complaint.complaint_code} Escalated to Level {level}"
    body = (
        f"Grievance Case Escalation Notice\n"
        f"----------------------------------------\n"
        f"Case Reference: {complaint.complaint_code}\n"
        f"Escalation Level: L{level}\n"
        f"Institution: {inst_name}\n"
        f"Cell: {cell_name}\n"
        f"Priority: {complaint.priority}\n"
        f"SLA Due Time: {due_str}\n"
        f"Current Status: {complaint.get_status_display()}\n\n"
        f"Action Required: Please review this matter immediately in the Resolve_Hub Command Centre.\n"
        f"Note: Complainant personal identity is restricted and accessible only to authorized officers."
    )

    channel = "EMAIL"
    if recipient and recipient.email:
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.warning("Failed to send escalation email to %s: %s", recipient.email, exc)

    return body


def run_escalation_check(now=None) -> list[EscalationEvent]:
    """
    Pure logic + ORM function that evaluates complaints against SLA windows
    and triggers upward escalations (L1, L2, L3).
    Idempotent: will never duplicate an escalation event for the same level.
    """
    if now is None:
        now = timezone.now()

    # Closed or resolved or spam complaints are NEVER escalated
    active_complaints = Complaint.objects.select_related(
        "institution", "cell", "cell__bureau"
    ).exclude(
        status__in=[Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]
    ).filter(
        sla_due_at__isnull=False
    )

    escalation_events = []

    for complaint in active_complaints:
        # If complaint SLA is paused (e.g. AWAITING_COMPLAINANT), do not advance escalation
        if complaint.status == Status.AWAITING_COMPLAINANT:
            continue

        created_at = complaint.created_at
        sla_due_at = complaint.sla_due_at

        # Total SLA window allocated
        total_window = sla_due_at - created_at
        if total_window.total_seconds() <= 0:
            total_window = timedelta(hours=24)

        elapsed = now - created_at
        ratio = elapsed.total_seconds() / total_window.total_seconds()

        target_level = complaint.escalation_level

        # L3 Criteria:
        # elapsed >= 2x SLA (ratio >= 2.0) OR (is_court_rti and ratio >= 1.0)
        if ratio >= 2.0 or (complaint.is_court_rti and ratio >= 1.0):
            target_level = max(target_level, 3)
        # L2 Criteria: breached SLA (ratio >= 1.0)
        elif ratio >= 1.0:
            target_level = max(target_level, 2)
        # L1 Criteria: 80% elapsed (ratio >= 0.80)
        elif ratio >= 0.80:
            target_level = max(target_level, 1)

        # Only escalate UPWARD
        if target_level > complaint.escalation_level:
            for lvl in range(complaint.escalation_level + 1, target_level + 1):
                # Check idempotency: has this level already been recorded?
                if EscalationEvent.objects.filter(complaint=complaint, level=lvl).exists():
                    continue

                # Identify officer to notify
                officer = None
                if lvl == 1:
                    # Notify Section Head of the complaint's cell
                    if complaint.cell:
                        officer = User.objects.filter(role=Role.SECTION_HEAD, cell=complaint.cell).first()
                elif lvl == 2:
                    # Notify Bureau Head
                    if complaint.cell and complaint.cell.bureau:
                        officer = User.objects.filter(role=Role.BUREAU_HEAD, bureau=complaint.cell.bureau).first()
                elif lvl == 3:
                    # Notify Member Secretary or Director
                    officer = (
                        User.objects.filter(role=Role.MEMBER_SECRETARY).first()
                        or User.objects.filter(role=Role.DIRECTOR).first()
                    )

                msg = _send_escalation_notification(complaint, lvl, officer)

                event = EscalationEvent.objects.create(
                    complaint=complaint,
                    level=lvl,
                    triggered_at=now,
                    notified_user=officer,
                    channel="EMAIL",
                    message=msg,
                )
                escalation_events.append(event)

                log_action(
                    actor=officer,
                    action=f"ESCALATION_L{lvl}_TRIGGERED",
                    target=f"complaint:{complaint.pk}",
                    metadata={
                        "level": lvl,
                        "ratio": round(ratio, 2),
                        "officer": officer.email if officer else "None",
                    },
                )

            complaint.escalation_level = target_level
            complaint.save(update_fields=["escalation_level"])

    return escalation_events

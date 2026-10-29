from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Department


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "complaint categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Status(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    AWAITING_COMPLAINANT = "AWAITING_COMPLAINANT", "Awaiting Complainant"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"
    SPAM = "SPAM", "Spam"
    CLOSED = "CLOSED", "Closed"


# Lifecycle stage mapping for backward compatibility and modern AICTE view:
# Logged -> Triaged -> Assigned -> Action -> Closed
LIFECYCLE_MAPPING = {
    Status.SUBMITTED: "Logged",
    Status.UNDER_REVIEW: "Triaged",
    Status.IN_PROGRESS: "Assigned",
    Status.AWAITING_COMPLAINANT: "Action",
    Status.RESOLVED: "Action",
    Status.CLOSED: "Closed",
    Status.REJECTED: "Closed",
    Status.SPAM: "Closed",
}


class Urgency(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class PriorityLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class SourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    EMAIL = "EMAIL", "Email"
    LETTER_OCR = "LETTER_OCR", "Letter OCR"
    CPGRAMS = "CPGRAMS", "CPGRAMS"
    COURT = "COURT", "Court"
    RTI = "RTI", "RTI"
    PARLIAMENT = "PARLIAMENT", "Parliament"


class SpamClassification(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    REVIEW = "REVIEW", "Review"
    SUSPICIOUS = "SUSPICIOUS", "Suspicious"


def _generate_complaint_code():
    year = timezone.now().year
    return f"RH-{year}-{uuid.uuid4().hex[:6].upper()}"


class Complaint(models.Model):
    """
    Central Complaint record for Resolve_Hub.
    Intake occurs through register_complaint(...) only.
    """

    complaint_code = models.CharField(
        max_length=32, unique=True, default=_generate_complaint_code, editable=False
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        ComplaintCategory, on_delete=models.PROTECT, related_name="complaints"
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="complaints",
    )
    cell = models.ForeignKey(
        "institutions.Cell",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )

    subject = models.CharField(max_length=200)
    description = models.TextField()
    department_or_location = models.CharField(max_length=200, blank=True)
    student_urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM)

    source_channel = models.CharField(
        max_length=20, choices=SourceChannel.choices, default=SourceChannel.WEB
    )
    language = models.CharField(max_length=10, default="en")
    priority = models.CharField(
        max_length=20, choices=PriorityLevel.choices, default=PriorityLevel.MEDIUM
    )
    triage_confidence = models.FloatField(default=0.0)
    triage_needs_review = models.BooleanField(default=False)

    status = models.CharField(max_length=25, choices=Status.choices, default=Status.SUBMITTED)

    # SLA and Escalation
    sla_due_at = models.DateTimeField(null=True, blank=True)
    sla_paused_at = models.DateTimeField(null=True, blank=True)
    sla_paused_total = models.DurationField(default=timedelta(0))
    escalation_level = models.PositiveSmallIntegerField(default=0)

    # Court & RTI flags
    is_court_rti = models.BooleanField(default=False)
    court_rti_reference = models.CharField(max_length=100, blank=True, default="")

    # Duplicate linking (same institution)
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicates"
    )
    external_reference = models.CharField(max_length=100, blank=True, default="", db_index=True)

    # Privacy & Consent
    is_confidential = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=20, blank=True, default="1.0")
    complainant_contact_hash = models.CharField(max_length=128, blank=True, default="", db_index=True)

    # Spam scoring summary
    spam_score = models.PositiveSmallIntegerField(default=0)
    spam_classification = models.CharField(
        max_length=12, choices=SpamClassification.choices, default=SpamClassification.NORMAL
    )

    director_public_remark = models.TextField(blank=True)
    director_internal_note = models.TextField(blank=True)

    # Institutional Registry and Officer Assignment
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    assigned_officer_name = models.CharField(max_length=150, blank=True, default="")
    registry_status = models.CharField(max_length=60, blank=True, default="")
    csv_sla_status = models.CharField(max_length=50, blank=True, default="")
    date_received = models.DateField(null=True, blank=True)
    is_sample_data = models.BooleanField(default=False)

    # Legacy routing support
    assigned_department = models.CharField(
        max_length=20, choices=Department.choices, null=True, blank=True
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_forwarded",
    )
    hod_remark = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "created_at"]),
            models.Index(fields=["institution", "created_at"]),
            models.Index(fields=["cell", "created_at"]),
            models.Index(fields=["priority", "created_at"]),
            models.Index(fields=["escalation_level", "created_at"]),
            models.Index(fields=["spam_classification", "created_at"]),
            models.Index(fields=["assigned_department", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint_code} ({self.status})"

    @property
    def lifecycle_stage(self) -> str:
        return LIFECYCLE_MAPPING.get(self.status, "Logged")

    @property
    def is_sla_breached(self) -> bool:
        if not self.sla_due_at:
            return False
        if self.status in [Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]:
            return False
        return timezone.now() > self.sla_due_at

    @property
    def sla_countdown_info(self) -> dict:
        now = timezone.now()
        is_completed = self.status in [Status.RESOLVED, Status.CLOSED, Status.REJECTED, Status.SPAM]
        if is_completed:
            return {
                "label": "Resolved / Closed",
                "badge_text": "Resolved / Closed",
                "state": "COMPLETED",
                "status": "COMPLETED",
                "badge_class": "bg-success text-white",
                "remaining_seconds": 0,
                "days_remaining": 0,
                "hours_remaining": 0,
                "percent_elapsed": 100,
                "is_breached": False,
                "is_approaching": False,
                "mismatch_flag": False,
                "mismatch_reason": "",
            }

        if not self.sla_due_at:
            return {
                "label": "Deadline Unavailable",
                "badge_text": "Deadline Unavailable",
                "state": "UNAVAILABLE",
                "status": "UNAVAILABLE",
                "badge_class": "bg-secondary text-white",
                "remaining_seconds": None,
                "days_remaining": None,
                "hours_remaining": None,
                "percent_elapsed": 0,
                "is_breached": False,
                "is_approaching": False,
                "mismatch_flag": bool(self.csv_sla_status),
                "mismatch_reason": "No SLA deadline defined in policy or case record." if self.csv_sla_status else "",
            }

        diff = (self.sla_due_at - now).total_seconds()
        is_breached = diff < 0

        # Mismatch check with imported CSV status
        mismatch_flag = False
        mismatch_reason = ""
        csv_s = (self.csv_sla_status or "").strip().lower()
        if csv_s:
            if "on track" in csv_s and is_breached:
                mismatch_flag = True
                mismatch_reason = "Stored as 'On Track', but deadline has passed and case is breached."
            elif "overdue" in csv_s and not is_breached:
                mismatch_flag = True
                mismatch_reason = "Stored as 'Overdue', but current deadline is still in the future."
            elif "resolved" in csv_s and not is_completed:
                mismatch_flag = True
                mismatch_reason = "Stored as 'Resolved Within SLA', but case status remains unresolved."

        if is_breached:
            overdue_seconds = abs(diff)
            days = int(overdue_seconds // 86400)
            hours = int((overdue_seconds % 86400) // 3600)
            minutes = int((overdue_seconds % 3600) // 60)
            if days > 0:
                label = f"SLA breached by {days}d {hours}h (Overdue)"
            elif hours > 0:
                label = f"SLA breached by {hours}h {minutes}m (Overdue)"
            else:
                label = f"SLA breached by {max(1, minutes)}m (Overdue)"

            return {
                "label": label,
                "badge_text": label,
                "state": "BREACHED",
                "status": "BREACHED",
                "badge_class": "bg-danger text-white",
                "remaining_seconds": int(diff),
                "days_remaining": -days,
                "hours_remaining": -hours,
                "percent_elapsed": 100,
                "is_breached": True,
                "is_approaching": False,
                "mismatch_flag": mismatch_flag,
                "mismatch_reason": mismatch_reason,
            }

        # Not breached, deadline in future
        remaining_seconds = int(diff)
        days = int(remaining_seconds // 86400)
        hours = int((remaining_seconds % 86400) // 3600)
        minutes = int((remaining_seconds % 3600) // 60)

        # Elapsed percentage
        total_window = None
        percent_elapsed = 50
        if self.date_received and self.sla_due_at > self.date_received:
            total_window = (self.sla_due_at - self.date_received).total_seconds()
            elapsed_sec = (now - self.date_received).total_seconds()
            if total_window > 0:
                percent_elapsed = min(100, max(0, int((elapsed_sec / total_window) * 100)))

        if days > 0:
            label = f"{days}d {hours}h remaining" if days > 1 else f"1d {hours}h remaining"
            state = "ON_TRACK"
            status = "ON_TRACK"
            badge_class = "bg-success text-white"
            is_approaching = False
        elif hours > 1:
            label = f"{hours}h remaining (Due today)"
            state = "APPROACHING"
            status = "AT_RISK"
            badge_class = "bg-warning text-dark"
            is_approaching = True
        elif hours == 1:
            label = f"1h {minutes}m remaining"
            state = "APPROACHING"
            status = "AT_RISK"
            badge_class = "bg-warning text-dark"
            is_approaching = True
        else:
            label = f"{max(1, minutes)}m remaining (Due now)"
            state = "DUE_NOW"
            status = "AT_RISK"
            badge_class = "bg-danger text-white"
            is_approaching = True

        return {
            "label": label,
            "badge_text": label,
            "state": state,
            "status": status,
            "badge_class": badge_class,
            "remaining_seconds": remaining_seconds,
            "days_remaining": days,
            "hours_remaining": hours,
            "percent_elapsed": percent_elapsed,
            "is_breached": False,
            "is_approaching": is_approaching,
            "mismatch_flag": mismatch_flag,
            "mismatch_reason": mismatch_reason,
        }

    @property
    def related_from(self):
        return self.relationships_from

    @property
    def related_to(self):
        return self.relationships_to


class CategoryCellRoute(models.Model):
    category = models.OneToOneField(
        ComplaintCategory, on_delete=models.CASCADE, related_name="cell_route"
    )
    cell = models.ForeignKey(
        "institutions.Cell", on_delete=models.CASCADE, related_name="category_routes"
    )

    def __str__(self):
        return f"{self.category.name} -> {self.cell.name}"


class EscalationEvent(models.Model):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="escalation_events"
    )
    level = models.PositiveSmallIntegerField()
    triggered_at = models.DateTimeField(default=timezone.now)
    notified_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalation_notifications",
    )
    channel = models.CharField(max_length=20, default="EMAIL")
    message = models.TextField()

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"{self.complaint.complaint_code} escalated to L{self.level} at {self.triggered_at}"


class Attachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    storage_path = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=25, choices=Status.choices, blank=True)
    new_status = models.CharField(max_length=25, choices=Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="status_changes"
    )
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint.complaint_code}: {self.old_status} -> {self.new_status}"


class AICaseIntelligence(models.Model):
    """
    Dedicated AI intelligence profile for every complaint,
    storing structured summary, facts, regulatory analysis, and recommendations.
    """
    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="ai_intelligence"
    )
    summary = models.TextField(blank=True, default="")
    main_issue = models.CharField(max_length=255, blank=True, default="")
    relevant_institution = models.CharField(max_length=255, blank=True, default="")
    relevant_department = models.CharField(max_length=120, blank=True, default="")
    relevant_bureau = models.CharField(max_length=120, blank=True, default="")
    relevant_cell = models.CharField(max_length=120, blank=True, default="")
    important_facts = models.JSONField(default=list, blank=True)
    missing_evidence = models.JSONField(default=list, blank=True)
    suggested_urgency = models.CharField(max_length=30, blank=True, default="Medium")
    regulatory_concerns = models.JSONField(default=list, blank=True)
    recommended_action = models.TextField(blank=True, default="")
    recommended_action_rationale = models.TextField(blank=True, default="")
    required_documents = models.JSONField(default=list, blank=True)
    suggested_responsible_role = models.CharField(max_length=150, blank=True, default="")
    action_checklist = models.JSONField(default=list, blank=True)
    followup_escalation = models.TextField(blank=True, default="")
    predicted_category = models.CharField(max_length=100, blank=True, default="")
    confidence_score = models.FloatField(default=0.0)
    is_rule_fallback = models.BooleanField(default=False)
    model_name = models.CharField(max_length=100, default="ResolveHub-Triage-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def facts(self):
        return self.important_facts

    @property
    def action_rationale(self):
        return self.recommended_action_rationale

    @property
    def recommendation_actions(self):
        return self.complaint.recommendation_actions.all()

    def __str__(self):
        return f"AI Intelligence for {self.complaint.complaint_code}"


class AIRecommendationAction(models.Model):
    """
    Tracks officer decisions on individual AI next-step recommendations.
    """
    class ActionState(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        DISMISSED = "DISMISSED", "Dismissed"
        NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="recommendation_actions"
    )
    recommendation_title = models.CharField(max_length=255)
    action_state = models.CharField(
        max_length=25, choices=ActionState.choices, default=ActionState.PENDING
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendation_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.complaint.complaint_code} - {self.recommendation_title} ({self.action_state})"

    @property
    def title(self):
        return self.recommendation_title

    @property
    def status(self):
        return self.action_state

    @status.setter
    def status(self, val):
        self.action_state = val

    def get_status_display(self):
        return self.get_action_state_display()

    @property
    def officer_notes(self):
        return self.notes

    @officer_notes.setter
    def officer_notes(self, val):
        self.notes = val


class LegalAttentionReview(models.Model):
    """
    Maintains human-in-the-loop review state and reasons for potential legal/urgent flags.
    """
    class FlagLevel(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine Review"
        PRIORITY = "PRIORITY", "Priority Review"
        LEGAL = "LEGAL", "Potential Legal Review"
        URGENT = "URGENT", "Urgent Human Review"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Human Review"
        CONFIRMED = "CONFIRMED", "Confirmed"
        DISMISSED = "DISMISSED", "Dismissed"
        REVISED = "REVISED", "Revised"
        REFERRED_LEGAL = "REFERRED_LEGAL", "Referred to Legal Bureau"

    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="legal_review"
    )
    flag_level = models.CharField(
        max_length=30, choices=FlagLevel.choices, default=FlagLevel.ROUTINE
    )
    suggested_flag = models.CharField(max_length=30, default="ROUTINE")
    suggested_reason = models.TextField(blank=True, default="")
    evidence_excerpt = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legal_reviews_conducted",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")
    referred_authority = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def reason(self):
        return self.suggested_reason

    @reason.setter
    def reason(self, val):
        self.suggested_reason = val

    def __str__(self):
        return f"{self.complaint.complaint_code} Legal Review: {self.flag_level} ({self.status})"


class ComplaintRelationship(models.Model):
    """
    Tracks related complaints from the same institution and duplicate detection candidate links.
    """
    class RelationshipType(models.TextChoices):
        SAME_INSTITUTION = "SAME_INSTITUTION", "Same Institution"
        SAME_TOPIC = "SAME_TOPIC", "Same Topic"
        SIMILAR_COMPLAINT = "SIMILAR_COMPLAINT", "Similar Complaint"
        POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE", "Potential Duplicate"
        CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE", "Confirmed Duplicate"
        REJECTED_DUPLICATE = "REJECTED_DUPLICATE", "Rejected Duplicate"

    source_complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="relationships_from"
    )
    target_complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="relationships_to"
    )
    relationship_type = models.CharField(
        max_length=30, choices=RelationshipType.choices, default=RelationshipType.SAME_INSTITUTION
    )
    similarity_score = models.FloatField(default=0.0)
    is_confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_relationships",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("source_complaint", "target_complaint"),)
        ordering = ["-similarity_score", "-created_at"]

    def __str__(self):
        return f"{self.source_complaint.complaint_code} -> {self.target_complaint.complaint_code} ({self.relationship_type})"


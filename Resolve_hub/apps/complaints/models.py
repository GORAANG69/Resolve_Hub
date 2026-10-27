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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints"
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
    def priority_explanation(self) -> str:
        if hasattr(self, "_cached_priority_explanation"):
            return self._cached_priority_explanation
        from .priority import get_complaint_priority_summary
        return get_complaint_priority_summary(self)

    @property
    def priority_badge_class(self) -> str:
        from .priority import get_priority_badge_class
        return get_priority_badge_class(self.priority)


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

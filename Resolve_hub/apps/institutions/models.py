from django.db import models
from django.utils import timezone


class InstitutionType(models.TextChoices):
    ENGINEERING = "ENGINEERING", "Engineering & Technology"
    MANAGEMENT = "MANAGEMENT", "Management"
    PHARMACY = "PHARMACY", "Pharmacy"
    ARCHITECTURE = "ARCHITECTURE", "Architecture"
    POLYTECHNIC = "POLYTECHNIC", "Polytechnic / Diploma"
    OTHER = "OTHER", "Other Technical Institution"


class Institution(models.Model):
    aicte_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=100, db_index=True)
    district = models.CharField(max_length=100)
    institution_type = models.CharField(
        max_length=32,
        choices=InstitutionType.choices,
        default=InstitutionType.ENGINEERING,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.aicte_id})"


class Bureau(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Cell(models.Model):
    bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name="cells")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    default_sla_hours = models.PositiveIntegerField(default=168)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.bureau.name})"


class PriorityLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class SLAPolicy(models.Model):
    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name="sla_policies")
    category = models.ForeignKey(
        "complaints.ComplaintCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sla_policies",
    )
    priority = models.CharField(max_length=20, choices=PriorityLevel.choices)
    sla_hours = models.PositiveIntegerField()

    class Meta:
        unique_together = (("cell", "category", "priority"),)

    def __str__(self) -> str:
        cat = self.category.name if self.category else "All Categories"
        return f"{self.cell.name} - {cat} - {self.priority}: {self.sla_hours}h"


class RiskBand(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class InstitutionRiskScore(models.Model):
    institution = models.OneToOneField(
        Institution,
        on_delete=models.CASCADE,
        related_name="risk_score",
    )
    score = models.FloatField(default=0.0)
    band = models.CharField(max_length=20, choices=RiskBand.choices, default=RiskBand.LOW)
    components = models.JSONField(default=dict)
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-score"]

    def __str__(self) -> str:
        return f"{self.institution.name}: {self.score:.1f} ({self.band})"

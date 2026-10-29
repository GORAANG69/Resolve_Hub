from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.complaints.models import Complaint, ComplaintCategory, Status
from apps.institutions.models import Institution, Cell, Bureau

class SLAMonitoringTestCase(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Public Grievance Cell", slug="pgc", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Fee Dispute", slug="fee-dispute")
        self.institution = Institution.objects.create(
            name="Apex Engineering College",
            aicte_id="1-99887766",
            state="Maharashtra",
            district="Pune",
        )

    def test_sla_on_track_countdown(self):
        """Case with deadline 5 days in future should be ON_TRACK with positive countdown."""
        due_at = timezone.now() + timedelta(days=5, hours=4)
        c = Complaint.objects.create(
            complaint_code="AICTE-SLA-01",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Delayed Caution Deposit Refund",
            status=Status.UNDER_REVIEW,
            sla_due_at=due_at,
        )
        sla_info = c.sla_countdown_info
        self.assertEqual(sla_info["status"], "ON_TRACK")
        self.assertFalse(sla_info["is_breached"])
        self.assertIn("remaining", sla_info["badge_text"])
        self.assertGreaterEqual(sla_info["days_remaining"], 4)

    def test_sla_at_risk_countdown(self):
        """Case with deadline less than 24 hours away should be AT_RISK."""
        due_at = timezone.now() + timedelta(hours=12)
        c = Complaint.objects.create(
            complaint_code="AICTE-SLA-02",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Impending Exam Registration Deadline",
            status=Status.IN_PROGRESS,
            sla_due_at=due_at,
        )
        sla_info = c.sla_countdown_info
        self.assertEqual(sla_info["status"], "AT_RISK")
        self.assertTrue(sla_info["is_approaching"])
        self.assertIn("h remaining", sla_info["badge_text"])

    def test_sla_breached_countdown(self):
        """Case with past deadline should be BREACHED with negative countdown."""
        past_due = timezone.now() - timedelta(days=2, hours=3)
        c = Complaint.objects.create(
            complaint_code="AICTE-SLA-03",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Unanswered Faculty Non-Payment Inquiry",
            status=Status.IN_PROGRESS,
            sla_due_at=past_due,
        )
        sla_info = c.sla_countdown_info
        self.assertEqual(sla_info["status"], "BREACHED")
        self.assertTrue(sla_info["is_breached"])
        self.assertIn("overdue", sla_info["badge_text"].lower())

    def test_resolved_case_is_not_breached(self):
        """Resolved or Closed cases must be COMPLETED and never BREACHED even if past deadline."""
        past_due = timezone.now() - timedelta(days=10)
        c = Complaint.objects.create(
            complaint_code="AICTE-SLA-04",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Resolved Equipment Inspection Complaint",
            status=Status.RESOLVED,
            resolved_at=timezone.now() - timedelta(days=8),
            sla_due_at=past_due,
        )
        sla_info = c.sla_countdown_info
        self.assertEqual(sla_info["status"], "COMPLETED")
        self.assertFalse(sla_info["is_breached"])
        self.assertIn("Resolved", sla_info["badge_text"])

    def test_sla_csv_reconciliation_mismatch(self):
        """Test reconciliation between stored CSV SLA status and real calculated deadline."""
        past_due = timezone.now() - timedelta(days=1)
        c = Complaint.objects.create(
            complaint_code="AICTE-SLA-05",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Mismatched SLA Status Case",
            status=Status.UNDER_REVIEW,
            sla_due_at=past_due,
            csv_sla_status="On Track",  # CSV claimed On Track, but time expired
        )
        sla_info = c.sla_countdown_info
        self.assertTrue(sla_info["mismatch_flag"])
        self.assertIn("breached", sla_info["mismatch_reason"].lower())

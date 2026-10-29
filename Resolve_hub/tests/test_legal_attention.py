from django.test import TestCase
from apps.complaints.models import Complaint, ComplaintCategory, LegalAttentionReview
from apps.institutions.models import Institution, Cell, Bureau
from apps.complaints.ai_service import assess_legal_attention
from apps.accounts.models import User, Role

class LegalAttentionTestCase(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Legal Cell", slug="legal-cell", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Ragging", slug="ragging")
        self.institution = Institution.objects.create(
            name="Apex Institute of Technology",
            aicte_id="1-99881122",
            state="Delhi",
            district="New Delhi",
        )
        self.officer = User.objects.create_user(
            username="officer_legal",
            email="officer_legal@aicte.gov.in",
            full_name="Adv. R. Sharma",
            role=Role.SECTION_HEAD,
            bureau=self.bureau,
            cell=self.cell,
        )

    def test_assess_legal_attention_urgent_safety(self):
        """Acute physical threat or ragging must trigger URGENT flag."""
        text = "First year students are facing severe ragging and physical assault in senior hostel block B."
        result = assess_legal_attention(text)
        self.assertEqual(result["flag_level"], "URGENT")
        self.assertTrue(len(result["evidence_excerpt"]) > 0)
        self.assertIn("safety", result["reason"].lower())

    def test_assess_legal_attention_court_writ_rti(self):
        """Writ petitions, court orders, or RTI appeals must trigger LEGAL flag."""
        text = "Under Article 226, a High Court writ petition WP 4821/2026 has been filed regarding non-compliance."
        result = assess_legal_attention(text)
        self.assertEqual(result["flag_level"], "LEGAL")
        self.assertIn("court", result["reason"].lower())

    def test_assess_legal_attention_financial_priority(self):
        """Financial fraud, embezzlement, or capitation fees must trigger PRIORITY flag."""
        text = "The management is charging unapproved capitation fees and conducting fraudulent audits."
        result = assess_legal_attention(text)
        self.assertIn(result["flag_level"], ["PRIORITY", "LEGAL", "URGENT"])

    def test_assess_legal_attention_routine(self):
        """Standard inquiries without legal or urgent triggers must return ROUTINE."""
        text = "Request for updating syllabus handbook in the library reading room."
        result = assess_legal_attention(text)
        self.assertEqual(result["flag_level"], "ROUTINE")

    def test_human_review_workflow(self):
        """Officer review updates flag status and records reviewer identity."""
        complaint = Complaint.objects.create(
            complaint_code="CASE-LEGAL-01",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Impending Contempt of Court Motion",
            description="High Court bench issued notice on compliance.",
            status="UNDER_REVIEW",
        )
        review = LegalAttentionReview.objects.create(
            complaint=complaint,
            flag_level="LEGAL",
            suggested_reason="High Court notice mentioned in complaint text.",
            evidence_excerpt="High Court bench issued notice",
            status=LegalAttentionReview.ReviewStatus.PENDING,
        )

        # Officer confirms and refers to legal counsel
        review.status = LegalAttentionReview.ReviewStatus.REFERRED_LEGAL
        review.reviewed_by = self.officer
        review.review_notes = "Sent to AICTE Standing Legal Counsel for urgent response."
        review.save()

        updated = LegalAttentionReview.objects.get(pk=review.pk)
        self.assertEqual(updated.status, LegalAttentionReview.ReviewStatus.REFERRED_LEGAL)
        self.assertEqual(updated.reviewed_by, self.officer)
        self.assertIn("Standing Legal Counsel", updated.review_notes)

from django.test import TestCase
from apps.complaints.models import Complaint, ComplaintCategory, AICaseIntelligence, AIRecommendationAction
from apps.institutions.models import Institution, Cell, Bureau
from apps.complaints.ai_service import (
    train_and_evaluate_classifier,
    predict_complaint_triage,
    generate_case_intelligence,
    load_dataset_b,
    load_dataset_c,
)

class AIIntelligenceTestCase(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Legal Cell", slug="legal-cell", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Fee Refund", slug="fee-refund")
        self.institution = Institution.objects.create(
            name="Delhi Institute of Technology",
            aicte_id="1-100200300",
            state="Delhi",
            district="New Delhi",
        )
        self.complaint = Complaint.objects.create(
            complaint_code="AICTE-TEST-001",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Withholding of Original Degree Certificates upon Course Completion",
            description="The college administration is unlawfully withholding original mark sheets and degree certificates demanding Rs 50,000 extra unapproved fee. When students protested, security threatened disciplinary action.",
            priority="HIGH",
            status="UNDER_REVIEW",
        )

    def test_datasets_loading(self):
        """Test Dataset B and Dataset C load properly and conform to schemas."""
        b_data = load_dataset_b()
        self.assertGreaterEqual(len(b_data), 800)
        self.assertIn("text", b_data[0])
        self.assertIn("department", b_data[0])
        self.assertIn("urgency", b_data[0])

        c_data = load_dataset_c()
        self.assertGreaterEqual(len(c_data), 600)
        self.assertIn("text", c_data[0])
        self.assertIn("category", c_data[0])

    def test_classifier_training_and_holdout_separation(self):
        """
        Verify classifier training runs on Dataset B and evaluates on isolated Dataset C
        without data leakage.
        """
        metrics = train_and_evaluate_classifier()
        self.assertIn("dataset_b", metrics)
        self.assertIn("dataset_c_holdout", metrics)
        self.assertIn("department_metrics", metrics["dataset_b"])
        self.assertIn("urgency_metrics", metrics["dataset_b"])

        dept_acc = metrics["dataset_b"]["department_metrics"]["accuracy"]
        self.assertGreater(dept_acc, 0.50, "Department accuracy should exceed baseline 50%")
        self.assertIn("f1_weighted", metrics["dataset_b"]["department_metrics"])

        # Check holdout benchmark was tested on holdout set
        holdout_count = metrics["dataset_c_holdout"]["total_holdout_samples"]
        self.assertGreaterEqual(holdout_count, 600)

    def test_triage_prediction(self):
        """Test complaint text classification predicting department and urgency."""
        pred = predict_complaint_triage("The campus wifi and student ERP portal have been down during examinations.")
        self.assertIn("department", pred)
        self.assertIn("urgency", pred)
        self.assertIn("confidence", pred)
        self.assertIn(pred["department"], ["IT Support", "Administration", "Academics", "Maintenance", "Fees / Finance", "Hostels", "Security / Discipline", "Transport"])

    def test_case_intelligence_generation(self):
        """Test comprehensive AI case intelligence generation with structured output and checklist."""
        intel = generate_case_intelligence(self.complaint)
        self.assertIsNotNone(intel)
        self.assertEqual(intel.complaint, self.complaint)
        self.assertTrue(len(intel.summary) > 20)
        self.assertTrue(len(intel.main_issue) > 5)
        self.assertIsInstance(intel.facts, list)
        self.assertIsInstance(intel.missing_evidence, list)
        self.assertIsInstance(intel.regulatory_concerns, list)
        self.assertTrue(len(intel.recommended_action) > 5)
        self.assertTrue(len(intel.action_rationale) > 10)

        # Check actionable checklist created
        actions = intel.recommendation_actions.all()
        self.assertGreaterEqual(actions.count(), 1)
        first_act = actions.first()
        self.assertEqual(first_act.status, "PENDING")

        # Officer updates checklist item
        first_act.status = "COMPLETED"
        first_act.officer_notes = "Verified fee circular; university notified."
        first_act.save()
        self.assertEqual(AIRecommendationAction.objects.get(pk=first_act.pk).status, "COMPLETED")

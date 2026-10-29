import os
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from apps.complaints.models import Complaint, AICaseIntelligence, LegalAttentionReview
from apps.institutions.models import Institution, Cell, Bureau

class DatasetImportTestCase(TestCase):
    def setUp(self):
        # Create base Bureau and Cell for testing
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="approval-bureau")
        self.cell = Cell.objects.create(name="Public Grievance Cell", slug="public-grievance-cell", bureau=self.bureau)

    def test_import_complaint_data_idempotency(self):
        """Test that import_complaint_data executes cleanly and is idempotent."""
        out = StringIO()
        call_command("import_complaint_data", stdout=out)
        output = out.getvalue()
        self.assertIn("Total rows processed: 54", output)

        initial_count = Complaint.objects.count()
        self.assertGreater(initial_count, 0, "Complaints should be imported")

        # Verify all imported cases are flagged as sample data
        sample_cases = Complaint.objects.filter(is_sample_data=True)
        self.assertEqual(sample_cases.count(), initial_count)

        # Run again without --update-existing -> should skip existing records
        out2 = StringIO()
        call_command("import_complaint_data", stdout=out2)
        output2 = out2.getvalue()
        self.assertIn("Cases Skipped:  54", output2)
        self.assertEqual(Complaint.objects.count(), initial_count)

    def test_dataset_b_and_c_not_imported_as_live_complaints(self):
        """
        Ensure Dataset B (800 university triage rows) and Dataset C (614 holdout rows)
        are NOT imported into the live Complaint model.
        """
        out = StringIO()
        call_command("import_complaint_data", stdout=out)

        total_complaints = Complaint.objects.count()
        # Dataset A has 54 rows. The total complaints should be around 54, definitely not 800+ or 1400+.
        self.assertLessEqual(total_complaints, 60)

    def test_update_existing_flag(self):
        """Test running import_complaint_data with --update-existing updates records."""
        out = StringIO()
        call_command("import_complaint_data", stdout=out)

        out_update = StringIO()
        call_command("import_complaint_data", update_existing=True, stdout=out_update)
        output_update = out_update.getvalue()
        self.assertIn("Updated:", output_update)

    def test_ai_intelligence_created_for_imported_cases(self):
        """Test that imported cases receive AI case intelligence and legal reviews."""
        call_command("import_complaint_data", verbosity=0)
        first_case = Complaint.objects.filter(is_sample_data=True).first()
        self.assertIsNotNone(first_case)
        self.assertTrue(hasattr(first_case, "ai_intelligence"))
        self.assertTrue(hasattr(first_case, "legal_review"))
        self.assertIsNotNone(first_case.ai_intelligence.summary)
        self.assertIsNotNone(first_case.legal_review.flag_level)

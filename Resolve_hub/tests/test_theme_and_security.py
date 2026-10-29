import json
from django.test import TestCase, Client
from apps.accounts.models import User, Role
from apps.complaints.models import Complaint, ComplaintCategory, Status
from apps.institutions.models import Institution, Cell, Bureau
from apps.officer_portal.views import _safe_officer_summary

class ThemeAndSecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Public Grievance Cell", slug="pgc", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Admissions", slug="admissions")
        self.institution = Institution.objects.create(
            name="Sardar Patel Institute",
            aicte_id="1-33445566",
            state="Gujarat",
            district="Ahmedabad",
        )

        # Complainant user (Student)
        self.student = User.objects.create_user(
            username="student_rahul",
            email="rahul.secret@gmail.com",
            mobile_number="9876543210",
            full_name="Rahul V. Sharma",
            roll_number="CS2026-999",
            role=Role.STUDENT,
        )

        # Officer user
        self.officer = User.objects.create_user(
            username="officer_patel",
            email="patel.officer@aicte.gov.in",
            full_name="Dr. V. Patel",
            role=Role.SECTION_HEAD,
            bureau=self.bureau,
            cell=self.cell,
        )

        # Complaint with sensitive student details
        self.complaint = Complaint.objects.create(
            complaint_code="AICTE-PII-SEC-01",
            student=self.student,
            institution=self.institution,
            cell=self.cell,
            category=self.category,
            subject="Irregular admission fee demand without receipt",
            description="College accounts office demanded Rs 25,000 in cash without receipt.",
            status=Status.UNDER_REVIEW,
        )

    def test_theme_api_anonymous_user(self):
        """Anonymous user can read default theme and update session theme."""
        resp = self.client.get("/api/theme/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("theme", data)

        # Set to Dark mode
        resp_post = self.client.post(
            "/api/theme/",
            data=json.dumps({"theme": "DARK"}),
            content_type="application/json",
        )
        self.assertEqual(resp_post.status_code, 200)
        self.assertEqual(resp_post.json()["theme"], "DARK")

    def test_theme_api_authenticated_user_persistence(self):
        """Authenticated user has theme persisted to database profile."""
        self.client.force_login(self.officer)
        resp_post = self.client.post(
            "/api/theme/",
            data=json.dumps({"theme": "DARK"}),
            content_type="application/json",
        )
        self.assertEqual(resp_post.status_code, 200)
        self.assertEqual(resp_post.json()["theme"], "DARK")

        # Verify DB updated
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.theme_preference, "DARK")

    def test_officer_summary_masks_all_student_pii(self):
        """
        Officer summary MUST NEVER include student name, email, roll number, or mobile number.
        Prevents accidental PII leaks under AICTE privacy guidelines.
        """
        summary = _safe_officer_summary(self.complaint)

        # Ensure dictionary has no keys revealing student identity
        self.assertNotIn("student", summary)
        self.assertNotIn("student_name", summary)
        self.assertNotIn("student_email", summary)
        self.assertNotIn("student_mobile", summary)
        self.assertNotIn("student_roll_number", summary)

        # Convert entire summary values to string and check no PII substring exists
        summary_repr = json.dumps(str(summary))
        self.assertNotIn("Rahul V. Sharma", summary_repr)
        self.assertNotIn("rahul.secret@gmail.com", summary_repr)
        self.assertNotIn("9876543210", summary_repr)
        self.assertNotIn("CS2026-999", summary_repr)

    def test_case_detail_api_masks_pii(self):
        """The public / officer Case Detail JSON endpoint must also not leak complainant PII."""
        self.client.force_login(self.officer)
        resp = self.client.get(f"/api/cases/{self.complaint.complaint_code}/")
        self.assertEqual(resp.status_code, 200)
        resp_text = resp.content.decode("utf-8")

        self.assertNotIn("Rahul V. Sharma", resp_text)
        self.assertNotIn("rahul.secret@gmail.com", resp_text)
        self.assertNotIn("9876543210", resp_text)
        self.assertNotIn("CS2026-999", resp_text)


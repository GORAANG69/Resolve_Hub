"""
Comprehensive tests for Feature A (Intelligent Complaint Prioritisation)
and Feature B (Institutional Complaint Trend Analysis).
"""
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.complaints.models import Complaint, ComplaintCategory, PriorityLevel, Status
from apps.complaints.priority import (
    compute_priority,
    get_complaint_priority_summary,
    get_priority_badge_class,
)
from apps.director_portal.analytics import compute_institutional_analytics
from apps.institutions.models import Institution
from .test_authorization import make_director, make_student


class ComplaintPrioritisationUnitTests(TestCase):
    """Unit tests for pure-Python priority scoring engine."""

    def setUp(self):
        self.category = ComplaintCategory.objects.create(name="Campus Safety", slug="safety")
        self.academic_category = ComplaintCategory.objects.create(name="Academics", slug="academics")
        self.institution = Institution.objects.create(
            aicte_id="1-TEST-001", name="National Institute of Technology", state="Delhi", district="New Delhi"
        )
        self.student = make_student()

    def test_critical_keyword_assigns_critical_priority(self):
        complaint = {
            "subject": "Severe ragging by senior students in hostel block",
            "description": "The victim was threatened with physical violence.",
            "category": self.category,
            "student_urgency": "HIGH",
            "status": "SUBMITTED",
        }
        level, score, reasons = compute_priority(complaint)
        self.assertEqual(level, PriorityLevel.CRITICAL)
        self.assertGreaterEqual(score, 70)
        self.assertTrue(any("Critical safety/harassment indicator" in r for r in reasons))

    def test_high_keyword_assigns_high_or_critical_priority(self):
        complaint = {
            "subject": "Bribe demanded for exam hall ticket clearance",
            "description": "Staff member asked for capitation fee in cash.",
            "category": self.academic_category,
            "student_urgency": "MEDIUM",
            "status": "SUBMITTED",
        }
        level, score, reasons = compute_priority(complaint)
        self.assertIn(level, [PriorityLevel.HIGH, PriorityLevel.CRITICAL])
        self.assertTrue(any("compliance or hazard" in r for r in reasons))

    def test_court_or_rti_flag_adds_high_score(self):
        complaint = {
            "subject": "Court inquiry regarding faculty appointment",
            "description": "High Court writ petition order copy attached.",
            "is_court_rti": True,
            "status": "SUBMITTED",
        }
        level, score, reasons = compute_priority(complaint)
        self.assertIn(level, [PriorityLevel.HIGH, PriorityLevel.CRITICAL])
        self.assertTrue(any("Court or RTI" in r for r in reasons))

    def test_resolved_complaint_does_not_escalate_solely_due_to_age(self):
        now = timezone.now()
        created_45_days_ago = now - timedelta(days=45)

        # 1. Unresolved complaint (open 45 days)
        open_complaint = {
            "subject": "Routine hostel room fan repair",
            "description": "Ceiling fan speed regulator is loose.",
            "category": self.academic_category,
            "student_urgency": "LOW",
            "status": Status.SUBMITTED,
            "created_at": created_45_days_ago,
        }
        open_level, open_score, open_reasons = compute_priority(open_complaint, {"now": now})

        # 2. Resolved complaint (created 45 days ago, now resolved)
        resolved_complaint = {
            "subject": "Routine hostel room fan repair",
            "description": "Ceiling fan speed regulator is loose.",
            "category": self.academic_category,
            "student_urgency": "LOW",
            "status": Status.RESOLVED,
            "created_at": created_45_days_ago,
        }
        res_level, res_score, res_reasons = compute_priority(resolved_complaint, {"now": now})

        # Resolved complaint must have lower score because age points are strictly suppressed
        self.assertLess(res_score, open_score)
        self.assertTrue(any("status is RESOLVED; age/overdue escalation suppressed" in r for r in res_reasons))
        self.assertTrue(any("Unresolved for 45 days" in r for r in open_reasons))

    def test_sla_overdue_handling_active_vs_closed(self):
        now = timezone.now()
        past_due = now - timedelta(days=3)

        active = {
            "subject": "Grade card mismatch",
            "description": "Marks in portal differ from sheet.",
            "status": Status.IN_PROGRESS,
            "sla_due_at": past_due,
        }
        closed = {
            "subject": "Grade card mismatch",
            "description": "Marks in portal differ from sheet.",
            "status": Status.CLOSED,
            "sla_due_at": past_due,
        }

        _, active_score, active_reasons = compute_priority(active, {"now": now})
        _, closed_score, closed_reasons = compute_priority(closed, {"now": now})

        self.assertGreater(active_score, closed_score)
        self.assertTrue(any("SLA deadline exceeded" in r for r in active_reasons))

    def test_recurring_complaints_escalates_score(self):
        complaint = {
            "subject": "Hostel mess unhygienic food",
            "description": "Mess food quality is unacceptable.",
            "status": Status.SUBMITTED,
        }
        level_no_repeat, score_no_repeat, _ = compute_priority(complaint, {"recurring_count": 0})
        level_repeat, score_repeat, reasons_repeat = compute_priority(complaint, {"recurring_count": 6})

        self.assertGreater(score_repeat, score_no_repeat)
        self.assertTrue(any("Recurring pattern" in r for r in reasons_repeat))

    def test_missing_and_incomplete_fields_handled_gracefully(self):
        # Empty dict or None must never raise exceptions
        level1, score1, reasons1 = compute_priority({})
        self.assertIn(level1, [PriorityLevel.LOW, PriorityLevel.MEDIUM])
        self.assertGreaterEqual(score1, 0)
        self.assertIsInstance(reasons1, list)

        level2, score2, reasons2 = compute_priority(None)
        self.assertIn(level2, [PriorityLevel.LOW, PriorityLevel.MEDIUM])

        partial = {
            "subject": None,
            "description": None,
            "institution": None,
            "category": None,
            "sla_due_at": None,
            "created_at": None,
        }
        level3, score3, reasons3 = compute_priority(partial)
        self.assertIsNotNone(level3)

    def test_priority_summary_and_badge_helpers(self):
        complaint = {
            "subject": "Ragging complaint",
            "description": "Threat to life",
            "status": "SUBMITTED",
        }
        summary = get_complaint_priority_summary(complaint)
        self.assertIn("Score:", summary)
        self.assertIn("ragging", summary.lower())

        self.assertEqual(get_priority_badge_class("CRITICAL"), "bg-danger text-white")
        self.assertEqual(get_priority_badge_class("HIGH"), "bg-warning text-dark")
        self.assertEqual(get_priority_badge_class("MEDIUM"), "bg-info text-dark")
        self.assertEqual(get_priority_badge_class("LOW"), "bg-secondary text-white")


class InstitutionalAnalyticsUnitTests(TestCase):
    """Unit tests for institutional trend analysis engine."""

    def setUp(self):
        self.cat_ragging = ComplaintCategory.objects.create(name="Anti Ragging", slug="anti-ragging")
        self.cat_infra = ComplaintCategory.objects.create(name="Infrastructure", slug="infra")
        self.cat_fees = ComplaintCategory.objects.create(name="Fee Refund", slug="fee-refund")

        self.inst1 = Institution.objects.create(
            aicte_id="1-ALPHA-01", name="Alpha Institute of Technology", state="Maharashtra", district="Pune"
        )
        self.inst2 = Institution.objects.create(
            aicte_id="1-BETA-02", name="Beta College of Engineering", state="Karnataka", district="Bengaluru"
        )
        self.student = make_student()

        # Create complaints for inst1 (5 total -> high volume)
        now = timezone.now()
        for i in range(3):
            Complaint.objects.create(
                student=self.student,
                institution=self.inst1,
                category=self.cat_ragging,
                subject=f"Ragging case {i+1}",
                description="Harassment incident in hostel.",
                priority=PriorityLevel.CRITICAL,
                status=Status.SUBMITTED,
                created_at=now - timedelta(days=5),
            )
        Complaint.objects.create(
            student=self.student,
            institution=self.inst1,
            category=self.cat_infra,
            subject="Library WiFi issue",
            description="No connectivity.",
            priority=PriorityLevel.LOW,
            status=Status.RESOLVED,
            created_at=now - timedelta(days=10),
            resolved_at=now - timedelta(days=2),
        )
        Complaint.objects.create(
            student=self.student,
            institution=self.inst1,
            category=self.cat_infra,
            subject="Water cooler not working",
            description="Drinking water problem.",
            priority=PriorityLevel.MEDIUM,
            status=Status.IN_PROGRESS,
            created_at=now - timedelta(days=20),
            sla_due_at=now - timedelta(days=1),  # Overdue
        )

        # Create 1 complaint for inst2
        Complaint.objects.create(
            student=self.student,
            institution=self.inst2,
            category=self.cat_fees,
            subject="Excess fee charge",
            description="Demanded extra lab charges.",
            priority=PriorityLevel.MEDIUM,
            status=Status.SUBMITTED,
            created_at=now - timedelta(days=15),
        )

    def test_compute_institutional_analytics_kpis_and_rankings(self):
        analytics = compute_institutional_analytics()

        kpis = analytics["kpis"]
        self.assertEqual(kpis["total_complaints"], 6)
        self.assertEqual(kpis["critical_high_count"], 3)
        self.assertEqual(kpis["pending_count"], 5)
        self.assertEqual(kpis["overdue_count"], 1)
        self.assertEqual(kpis["resolved_count"], 1)

        rankings = analytics["institution_rankings"]
        self.assertEqual(len(rankings), 2)
        # Inst1 should be ranked #1 with 5 complaints
        self.assertEqual(rankings[0]["institution__name"], "Alpha Institute of Technology")
        self.assertEqual(rankings[0]["total_count"], 5)
        self.assertEqual(rankings[0]["critical_high_count"], 3)
        self.assertEqual(rankings[0]["overdue_count"], 1)
        self.assertTrue(rankings[0]["is_high_volume"])

        # Inst2 ranked #2 with 1 complaint
        self.assertEqual(rankings[1]["institution__name"], "Beta College of Engineering")
        self.assertEqual(rankings[1]["total_count"], 1)

    def test_repeated_category_detection(self):
        analytics = compute_institutional_analytics()
        repeated = analytics["repeated_categories"]

        # Anti Ragging had 3 incidents in inst1, Infrastructure had 2 incidents in inst1
        inst1_cats = [r["category__name"] for r in repeated if r["institution__id"] == self.inst1.id]
        self.assertIn("Anti Ragging", inst1_cats)
        self.assertIn("Infrastructure", inst1_cats)

    def test_analytics_filtering_by_institution_and_category(self):
        # Filter by inst2 only
        filtered_inst = compute_institutional_analytics({"institution": str(self.inst2.id)})
        self.assertEqual(filtered_inst["kpis"]["total_complaints"], 1)
        self.assertEqual(len(filtered_inst["institution_rankings"]), 1)

        # Filter by Anti Ragging category slug
        filtered_cat = compute_institutional_analytics({"category": "anti-ragging"})
        self.assertEqual(filtered_cat["kpis"]["total_complaints"], 3)
        self.assertEqual(filtered_cat["kpis"]["critical_high_count"], 3)

    def test_analytics_empty_state_returns_zero_counts(self):
        empty = compute_institutional_analytics({"institution": "NonExistentCollegeXYZ"})
        self.assertEqual(empty["kpis"]["total_complaints"], 0)
        self.assertEqual(empty["institution_rankings"], [])
        self.assertEqual(empty["repeated_categories"], [])


class InstitutionalAnalyticsAndPriorityViewTests(TestCase):
    """Integration tests for views, authorization, and UI presentation."""

    def setUp(self):
        self.director = make_director()
        self.student = make_student()
        self.category = ComplaintCategory.objects.create(name="Admissions", slug="admissions")
        self.inst = Institution.objects.create(aicte_id="1-VIEW-01", name="IIT Delhi", state="Delhi")

        self.c_crit = Complaint.objects.create(
            student=self.student,
            institution=self.inst,
            category=self.category,
            subject="Life threatening assault on student",
            description="Victim admitted to hospital after violence in hostel.",
            priority=PriorityLevel.CRITICAL,
            status=Status.SUBMITTED,
        )
        self.c_low = Complaint.objects.create(
            student=self.student,
            institution=self.inst,
            category=self.category,
            subject="Classroom projector flickering",
            description="Projector cable is slightly loose in room 102.",
            priority=PriorityLevel.LOW,
            status=Status.SUBMITTED,
        )

    def test_anonymous_and_student_access_to_analytics_rejected(self):
        # Anonymous redirect
        url = reverse("director_portal:analytics")
        resp_anon = self.client.get(url)
        self.assertEqual(resp_anon.status_code, 302)

        # Student forbidden (403)
        self.client.force_login(self.student)
        resp_stud = self.client.get(url)
        self.assertEqual(resp_stud.status_code, 403)

    def test_director_access_to_analytics_and_institutional_analytics_alias(self):
        self.client.force_login(self.director)

        resp1 = self.client.get(reverse("director_portal:analytics"))
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, "Institutional Complaint Trend Analysis")
        self.assertContains(resp1, "IIT Delhi")

        resp2 = self.client.get(reverse("director_portal:institutional_analytics"))
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "IIT Delhi")

    def test_director_complaint_list_urgent_first_ordering(self):
        self.client.force_login(self.director)
        url = reverse("director_portal:complaint_list")

        # Default order is urgent-first: CRITICAL should appear before LOW
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        complaints_list = list(response.context["complaints"])
        self.assertGreaterEqual(len(complaints_list), 2)
        # First complaint in list should be CRITICAL
        self.assertEqual(complaints_list[0].priority, PriorityLevel.CRITICAL)

        # Filtering by priority=CRITICAL
        resp_crit = self.client.get(url, {"priority": "CRITICAL"})
        self.assertEqual(resp_crit.status_code, 200)
        crit_ids = [c.id for c in resp_crit.context["complaints"]]
        self.assertIn(self.c_crit.id, crit_ids)
        self.assertNotIn(self.c_low.id, crit_ids)

    def test_complaint_priority_badge_and_explanation_rendered_in_templates(self):
        # Student detail view
        self.client.force_login(self.student)
        resp_detail = self.client.get(reverse("complaints:detail", kwargs={"public_id": self.c_crit.complaint_code}))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, "CRITICAL")
        self.assertContains(resp_detail, "Priority Assessment")

        # Director detail view
        self.client.force_login(self.director)
        resp_dir_detail = self.client.get(reverse("director_portal:complaint_detail", kwargs={"pk": self.c_crit.pk}))
        self.assertEqual(resp_dir_detail.status_code, 200)
        self.assertContains(resp_dir_detail, "CRITICAL")
        self.assertContains(resp_dir_detail, "Priority Factor")

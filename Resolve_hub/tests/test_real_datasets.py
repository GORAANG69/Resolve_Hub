from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import Role, User
from apps.complaints.models import StudentFeedback, CitizenGrievance
from apps.complaints.analytics_services import (
    get_student_feedback_analytics,
    get_citizen_grievance_analytics,
)


class RealDatasetsModelAndServiceTests(TestCase):
    def setUp(self):
        # Create sample StudentFeedback
        StudentFeedback.objects.create(
            source_id="SF-TEST-0001",
            response_index=1,
            category="Teaching",
            sentiment_score=1,
            sentiment_label="Positive",
            feedback_text="Excellent faculty and guidance.",
        )
        StudentFeedback.objects.create(
            source_id="SF-TEST-0002",
            response_index=2,
            category="Lab Work",
            sentiment_score=-1,
            sentiment_label="Negative",
            feedback_text="Equipment needs replacement.",
        )

        # Create sample CitizenGrievance
        CitizenGrievance.objects.create(
            grievance_id="GRV-TEST-0001",
            text="Water supply has been interrupted for three days.",
            category="Water Supply",
            language="en",
            source_file="grievances_synthetic.csv",
        )
        CitizenGrievance.objects.create(
            grievance_id="GRV-TEST-0002",
            text="सड़क पर गड्ढे होने से दुर्घटना का खतरा है।",
            category="Roads & Infrastructure",
            language="hi",
            source_file="grievances_holdout_templates.csv",
        )

    def test_student_feedback_creation_and_fields(self):
        fb = StudentFeedback.objects.get(source_id="SF-TEST-0001")
        self.assertEqual(fb.category, "Teaching")
        self.assertEqual(fb.sentiment_score, 1)
        self.assertEqual(fb.sentiment_label, "Positive")
        self.assertEqual(fb.response_index, 1)

    def test_citizen_grievance_creation_and_fields(self):
        grv = CitizenGrievance.objects.get(grievance_id="GRV-TEST-0001")
        self.assertEqual(grv.category, "Water Supply")
        self.assertEqual(grv.language, "en")
        self.assertEqual(grv.source_file, "grievances_synthetic.csv")

        grv_hi = CitizenGrievance.objects.get(grievance_id="GRV-TEST-0002")
        self.assertEqual(grv_hi.language, "hi")

    def test_student_feedback_analytics_service(self):
        analytics = get_student_feedback_analytics()
        self.assertEqual(analytics["total_records"], 2)
        self.assertEqual(analytics["overall_sentiment"]["Positive"], 1)
        self.assertEqual(analytics["overall_sentiment"]["Negative"], 1)
        self.assertEqual(analytics["overall_sentiment"]["Neutral"], 0)
        self.assertAlmostEqual(analytics["sentiment_percentages"]["Positive"], 50.0)
        self.assertAlmostEqual(analytics["sentiment_percentages"]["Negative"], 50.0)
        self.assertEqual(len(analytics["category_summary"]), 2)

    def test_citizen_grievance_analytics_service(self):
        analytics = get_citizen_grievance_analytics()
        self.assertEqual(analytics["total_records"], 2)
        self.assertEqual(len(analytics["category_distribution"]), 2)
        self.assertEqual(analytics["language_distribution"]["en"], 1)
        self.assertEqual(analytics["language_distribution"]["hi"], 1)


class RealDatasetsAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.director = User.objects.create_user(
            username="director_test@resolvehub.gov.in",
            email="director_test@resolvehub.gov.in",
            password="pass12345_secure",
            full_name="Director Admin",
            role=Role.DIRECTOR,
        )

        # Seed test records
        for i in range(15):
            StudentFeedback.objects.create(
                source_id=f"SF-API-{i:04d}",
                response_index=i + 1,
                category="Teaching" if i % 2 == 0 else "Lab Work",
                sentiment_score=1 if i % 3 == 0 else (-1 if i % 3 == 1 else 0),
                sentiment_label="Positive" if i % 3 == 0 else ("Negative" if i % 3 == 1 else "Neutral"),
                feedback_text=f"Sample feedback text {i}",
            )
            CitizenGrievance.objects.create(
                grievance_id=f"GRV-API-{i:04d}",
                text=f"Citizen grievance complaint text {i} regarding municipal issues",
                category="Sanitation & Garbage" if i % 2 == 0 else "Water Supply",
                language="en",
                source_file="grievances_synthetic.csv",
            )

    def test_citizen_grievances_api(self):
        # 1. Basic pagination
        resp = self.client.get(reverse("command_centre:citizen_grievances_api"), {"page": 1, "page_size": 10})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_count"], 15)
        self.assertEqual(len(data["items"]), 10)
        self.assertEqual(data["total_pages"], 2)

        # 2. Category filter
        resp_cat = self.client.get(
            reverse("command_centre:citizen_grievances_api"),
            {"category": "Water Supply"}
        )
        self.assertEqual(resp_cat.status_code, 200)
        data_cat = resp_cat.json()
        self.assertTrue(all(item["category"] == "Water Supply" for item in data_cat["items"]))

        # 3. Search filter
        resp_search = self.client.get(
            reverse("command_centre:citizen_grievances_api"),
            {"q": "text 5"}
        )
        self.assertEqual(resp_search.status_code, 200)
        self.assertEqual(resp_search.json()["total_count"], 1)

    def test_student_feedback_api(self):
        # 1. Basic pagination
        resp = self.client.get(reverse("command_centre:student_feedback_api"), {"page": 1, "page_size": 10})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_count"], 15)
        self.assertEqual(len(data["items"]), 10)

        # 2. Sentiment filter
        resp_sent = self.client.get(
            reverse("command_centre:student_feedback_api"),
            {"sentiment": "1"}
        )
        self.assertEqual(resp_sent.status_code, 200)
        data_sent = resp_sent.json()
        self.assertTrue(all(item["sentiment_score"] == 1 for item in data_sent["items"]))

    def test_real_datasets_analytics_api(self):
        resp = self.client.get(reverse("command_centre:analytics_summary_api"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("student_feedback", data)
        self.assertIn("citizen_grievances", data)
        self.assertEqual(data["student_feedback"]["total_records"], 15)
        self.assertEqual(data["citizen_grievances"]["total_records"], 15)

    def test_csv_export_datasets(self):
        self.client.force_login(self.director)

        # 1. Export citizen grievances CSV
        resp_grv = self.client.get(reverse("command_centre:export_csv") + "?dataset=grievances")
        self.assertEqual(resp_grv.status_code, 200)
        self.assertEqual(resp_grv["Content-Type"], "text/csv")
        content_grv = resp_grv.content.decode("utf-8")
        self.assertIn("Grievance ID,Department Category,Language,Source File,Grievance Text,Created At", content_grv)
        self.assertIn("GRV-API-0000", content_grv)

        # 2. Export student feedback CSV
        resp_fb = self.client.get(reverse("command_centre:export_csv") + "?dataset=feedback")
        self.assertEqual(resp_fb.status_code, 200)
        self.assertEqual(resp_fb["Content-Type"], "text/csv")
        content_fb = resp_fb.content.decode("utf-8")
        self.assertIn("Source ID,Survey Response Index,Category,Sentiment Score,Sentiment Label,Feedback Text,Source Batch,Created At", content_fb)
        self.assertIn("SF-API-0000", content_fb)

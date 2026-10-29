import json
from unittest.mock import MagicMock
from django.test import TestCase, override_settings
from google.genai.errors import APIError

from apps.complaints.gemini_service import (
    GeminiModelManager,
    GeminiAuthenticationError,
    GeminiAllModelsFailedError,
    generate_gemini_case_intelligence,
)
from apps.complaints.models import Complaint, ComplaintCategory
from apps.institutions.models import Institution, Cell, Bureau
from apps.complaints.ai_service import generate_case_intelligence


class MockResponse:
    def __init__(self, text):
        self.text = text


class GeminiIntegrationTestCase(TestCase):
    def setUp(self):
        self.bureau = Bureau.objects.create(name="Approval Bureau", slug="ab")
        self.cell = Cell.objects.create(name="Public Grievance Cell", slug="pgc", bureau=self.bureau)
        self.category = ComplaintCategory.objects.create(name="Faculty", slug="faculty")
        self.institution = Institution.objects.create(
            name="Apex Institute of Technology",
            aicte_id="1-99887711",
            state="Delhi",
            district="New Delhi",
        )
        self.complaint = Complaint.objects.create(
            complaint_code="AICTE-GEMINI-TEST-01",
            category=self.category,
            institution=self.institution,
            cell=self.cell,
            subject="Biometric attendance manipulation and faculty shortage in ECE department",
            description="The institution administration is forging faculty biometric logs and running unapproved evening diploma shifts.",
            priority="HIGH",
            status="UNDER_REVIEW",
        )

        self.valid_ai_json = json.dumps({
            "summary": "Executive summary of biometric manipulation allegations.",
            "main_issue": "Biometric log manipulation and unapproved shifts.",
            "suggested_category": "Faculty & Attendance",
            "suggested_department": "Approval & Licensing Bureau",
            "suggested_urgency": "High",
            "facts": ["Manipulated biometric attendance records", "Unapproved evening shifts"],
            "missing_evidence": ["Raw server attendance logs", "Faculty salary slips"],
            "regulatory_concerns": ["AICTE Approval Process Handbook norm violation"],
            "recommended_action": "Order surprise Expert Visiting Committee inspection.",
            "action_rationale": "High-severity fraud allegation requiring on-ground verification.",
            "action_checklist": [
                "1. Direct regional officer to preserve server hard drives.",
                "2. Issue Show Cause Notice to Chairman.",
                "3. Constitute 3-member inspection team."
            ],
            "suggested_responsible_role": "Bureau Head (Approval)",
            "followup_escalation": "Escalate to Director General if unverified in 7 days.",
            "potential_legal_concerns": "Potential forgery under regulatory audit statutes.",
            "confidence_score": 0.94,
        })

    def test_scenario_1_primary_model_succeeds(self):
        """Test 1: Primary model succeeds without calling any fallbacks."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MockResponse(self.valid_ai_json)

        manager = GeminiModelManager(
            api_key="test-api-key-123",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite", "gemini-1.5-flash"],
            client=mock_client,
        )

        text, model_used = manager.generate_content_with_fallback("Analyze petition")
        self.assertEqual(model_used, "gemini-2.5-flash")
        self.assertIn("Biometric log manipulation", text)
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

    def test_scenario_2_primary_model_429_fallback_succeeds(self):
        """Test 2: Primary model returns HTTP 429 quota exhaustion; first fallback succeeds."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            APIError(429, "Rate limit exceeded for model gemini-2.5-flash. Please reduce request frequency."),
            MockResponse(self.valid_ai_json),
        ]

        manager = GeminiModelManager(
            api_key="test-api-key-123",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite", "gemini-1.5-flash"],
            client=mock_client,
        )

        text, model_used = manager.generate_content_with_fallback("Analyze petition")
        self.assertEqual(model_used, "gemini-2.5-flash-lite")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    def test_scenario_3_primary_model_503_fallback_succeeds(self):
        """Test 3: Primary model returns HTTP 503 service unavailable; first fallback succeeds."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            APIError(503, "The service is temporarily unavailable. Back off and retry."),
            MockResponse(self.valid_ai_json),
        ]

        manager = GeminiModelManager(
            api_key="test-api-key-123",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite", "gemini-1.5-flash"],
            client=mock_client,
        )

        text, model_used = manager.generate_content_with_fallback("Analyze petition")
        self.assertEqual(model_used, "gemini-2.5-flash-lite")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    def test_scenario_4_invalid_credentials_does_not_trigger_pointless_switching(self):
        """Test 4: Invalid API key (HTTP 401/403) halts immediately without cycling fallbacks."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = APIError(403, "API key not valid. Please pass a valid API key.")

        manager = GeminiModelManager(
            api_key="invalid-api-key",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite", "gemini-1.5-flash"],
            client=mock_client,
        )

        with self.assertRaises(GeminiAuthenticationError):
            manager.generate_content_with_fallback("Analyze petition")

        # Crucial check: only called once! Did not cycle through fallback models!
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

    def test_scenario_5_all_models_fail_gracefully(self):
        """Test 5: All models in the chain fail with recoverable errors, raising GeminiAllModelsFailedError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            APIError(429, "429 Quota exceeded on gemini-2.5-flash"),
            APIError(429, "429 Quota exceeded on gemini-2.5-flash-lite"),
            APIError(503, "503 Unavailable on gemini-1.5-flash"),
        ]

        manager = GeminiModelManager(
            api_key="test-key",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite", "gemini-1.5-flash"],
            client=mock_client,
        )

        with self.assertRaises(GeminiAllModelsFailedError):
            manager.generate_content_with_fallback("Analyze petition")

        # Tested all 3 models in order
        self.assertEqual(mock_client.models.generate_content.call_count, 3)

    def test_scenario_6_original_request_context_preserved_during_fallback(self):
        """Test 6: Verify prompt and configuration are preserved verbatim across fallback attempts."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            APIError(429, "Quota limit"),
            MockResponse(self.valid_ai_json),
        ]

        manager = GeminiModelManager(
            api_key="test-key",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite"],
            client=mock_client,
        )

        test_prompt = "Official AICTE dossier for Case AICTE-GEMINI-TEST-01"
        test_sys_instruction = "Preserve administrative integrity"
        manager.generate_content_with_fallback(
            prompt=test_prompt,
            system_instruction=test_sys_instruction,
            temperature=0.25,
        )

        # Inspect calls to ensure context was identically preserved
        call_1_kwargs = mock_client.models.generate_content.call_args_list[0].kwargs
        call_2_kwargs = mock_client.models.generate_content.call_args_list[1].kwargs

        self.assertEqual(call_1_kwargs["contents"], test_prompt)
        self.assertEqual(call_2_kwargs["contents"], test_prompt)
        self.assertEqual(call_1_kwargs["model"], "gemini-2.5-flash")
        self.assertEqual(call_2_kwargs["model"], "gemini-2.5-flash-lite")

    @override_settings(GEMINI_API_KEY="")
    def test_scenario_7_non_ai_and_local_ml_fallback_works_without_gemini_credentials(self):
        """Test 7: When GEMINI_API_KEY is empty, seamlessly falls back to local ML with zero crash."""
        intel = generate_case_intelligence(self.complaint)
        self.assertIsNotNone(intel)
        self.assertEqual(intel.model_name, "ResolveHub-LocalML")
        self.assertTrue(len(intel.summary) > 10)
        self.assertTrue(len(intel.recommended_action) > 5)
        # Check that recommendation checklist actions were created
        self.assertGreaterEqual(self.complaint.recommendation_actions.count(), 1)

    def test_gemini_case_intelligence_end_to_end_with_mock(self):
        """Verify full complaint intelligence generation and model attribution."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            APIError(429, "429 Quota limit on primary"),
            MockResponse(self.valid_ai_json),
        ]

        manager = GeminiModelManager(
            api_key="test-key",
            primary_model="gemini-2.5-flash",
            fallback_models=["gemini-2.5-flash-lite"],
            client=mock_client,
        )

        intel = generate_gemini_case_intelligence(self.complaint, manager=manager)
        self.assertEqual(intel.model_name, "Gemini (gemini-2.5-flash-lite)")
        self.assertEqual(intel.confidence_score, 0.94)
        self.assertIn("biometric attendance records", intel.important_facts[0].lower())
        self.assertIn("Show Cause Notice", intel.action_checklist[1])


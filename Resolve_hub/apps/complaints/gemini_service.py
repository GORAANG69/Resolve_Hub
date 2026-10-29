import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Exceptions for Gemini Model Fallback
class GeminiError(Exception):
    """Base exception for Gemini service."""
    pass

class GeminiAuthenticationError(GeminiError):
    """Raised when API credentials are missing, invalid, or forbidden (HTTP 401, 403)."""
    pass

class GeminiAllModelsFailedError(GeminiError):
    """Raised when all models in the prioritized fallback chain fail."""
    def __init__(self, message: str, errors: Optional[List[Tuple[str, Exception]]] = None):
        super().__init__(message)
        self.errors = errors or []


class GeminiModelManager:
    """
    Centralized model manager providing intelligent model fallback across a prioritized chain:
    1. Primary model (e.g., gemini-2.5-flash)
    2. First fallback model (e.g., gemini-2.5-flash-lite)
    3. Additional fallback models (e.g., gemini-1.5-flash)
    
    Handles recoverable transient failures (HTTP 429, 503, 500, timeouts) by switching models,
    while terminating immediately without pointless switching on non-recoverable errors
    (HTTP 400 Bad Request, 401 Unauthorized, 403 Forbidden).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "GEMINI_API_KEY", "")
        self.primary_model = primary_model or getattr(settings, "GEMINI_PRIMARY_MODEL", "gemini-2.5-flash")
        
        fallbacks = fallback_models or getattr(settings, "GEMINI_FALLBACK_MODELS", ["gemini-2.5-flash-lite", "gemini-1.5-flash"])
        if isinstance(fallbacks, str):
            fallbacks = [m.strip() for m in fallbacks.split(",") if m.strip()]
        self.fallback_models = fallbacks

        # Assembled prioritized chain without duplicates
        chain = [self.primary_model]
        for m in self.fallback_models:
            if m not in chain:
                chain.append(m)
        self.model_chain = chain
        self._client = client

    def get_client(self):
        """Lazy initialization of the official Google GenAI Client."""
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise GeminiAuthenticationError("GEMINI_API_KEY is not configured in settings or environment.")

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except Exception as e:
            raise GeminiAuthenticationError(f"Failed to initialize google.genai Client: {e}")

    def is_recoverable_error(self, exc: Exception) -> Tuple[bool, str]:
        """
        Determines whether an exception is recoverable via model fallback.
        Returns (is_recoverable, reason).
        """
        err_str = str(exc).lower()

        # Check for google.genai APIError code
        code = getattr(exc, "code", None)
        if code is not None:
            if code in (401, 403):
                return False, f"Authentication/permission error ({code}). Switching models will not help."
            if code == 400:
                return False, f"Malformed request / invalid argument ({code}). Switching models will not help."
            if code == 429:
                # Distinguish account-wide quota exhaustion if explicit
                if "billing" in err_str or "account quota exceeded" in err_str:
                    return False, "Account-wide project quota exhausted. All models blocked."
                return True, "Model rate limit / quota exceeded (HTTP 429). Attempting fallback model."
            if code == 503:
                return True, "Model service temporarily unavailable (HTTP 503). Attempting fallback model."
            if code in (500, 502, 504):
                return True, f"Transient Google backend error (HTTP {code}). Attempting fallback model."

        # Check HTTP / network timeouts
        exc_type = type(exc).__name__.lower()
        if any(term in exc_type for term in ["timeout", "connecterror", "networkerror", "connection"]):
            return True, f"Transient network/timeout failure ({type(exc).__name__})."

        # Check error message strings for standard codes if code attribute wasn't explicit
        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
            return True, "Model rate limit or resource exhausted."
        if "503" in err_str or "unavailable" in err_str:
            return True, "Model service unavailable."
        if "500" in err_str or "internal" in err_str:
            return True, "Transient server error."

        return False, f"Non-recoverable exception: {type(exc).__name__}: {exc}"

    def generate_content_with_fallback(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = "application/json",
        temperature: float = 0.2,
    ) -> Tuple[str, str]:
        """
        Executes generation across the prioritized model chain.
        Returns (response_text, model_name_used).
        Raises GeminiAuthenticationError or GeminiAllModelsFailedError.
        """
        client = self.get_client()
        from google.genai import types

        errors_encountered = []

        for model_name in self.model_chain:
            try:
                config_kwargs = {"temperature": temperature}
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction
                if response_mime_type:
                    config_kwargs["response_mime_type"] = response_mime_type

                config = types.GenerateContentConfig(**config_kwargs)

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if response and hasattr(response, "text") and response.text:
                    return response.text, model_name
                raise GeminiError(f"Model {model_name} returned empty response.")

            except Exception as e:
                is_recoverable, reason = self.is_recoverable_error(e)
                errors_encountered.append((model_name, e))

                logger.warning(
                    f"[GeminiModelManager] Model '{model_name}' failed: {reason} | Raw Error: {e}"
                )

                if not is_recoverable:
                    if getattr(e, "code", None) in (401, 403) or "auth" in str(e).lower() or "api_key" in str(e).lower():
                        raise GeminiAuthenticationError(f"Gemini API authentication failed for model '{model_name}': {e}") from e
                    raise GeminiError(f"Non-recoverable error with model '{model_name}': {e}") from e

        # If all models in the fallback chain were exhausted
        chain_summary = " -> ".join(self.model_chain)
        raise GeminiAllModelsFailedError(
            f"All models in prioritized chain ({chain_summary}) failed recoverable calls.",
            errors=errors_encountered,
        )


def generate_gemini_case_intelligence(complaint, manager: Optional[GeminiModelManager] = None) -> Any:
    """
    Generates structured AI Case Intelligence for a Complaint using Google Gemini
    with automatic fallback across the model chain.
    """
    from apps.complaints.models import (
        AICaseIntelligence,
        AIRecommendationAction,
        LegalAttentionReview,
    )

    if manager is None:
        manager = GeminiModelManager()

    inst = complaint.institution
    inst_name = inst.name if inst else "Unassigned / General Technical Institution"
    inst_id = inst.aicte_id if inst else "N/A"
    cat_name = complaint.category.name if complaint.category else "Unspecified"
    cell_name = complaint.cell.name if complaint.cell else "Pending Allocation"
    bureau_name = complaint.cell.bureau.name if (complaint.cell and complaint.cell.bureau) else "Pending Allocation"

    system_instruction = (
        "You are an AICTE Regulatory Intelligence Analyst and Case Management Specialist for Resolve Hub. "
        "Analyze institutional grievance petitions against All India Council for Technical Education regulations. "
        "Provide factual, objective, explainable next steps based strictly on the case text. "
        "Never invent regulatory citations, court rulings, or statutory facts. "
        "Outputs are suggestions for authorized human officers and must not automatically close or resolve tickets. "
        "Return strictly valid JSON matching the requested fields."
    )

    prompt = f"""
Analyze the following technical education grievance record and generate structured case intelligence:

--- COMPLAINT DETAILS ---
Case ID: {complaint.complaint_code}
Institution: {inst_name} (AICTE ID: {inst_id})
Category: {cat_name}
Assigned Bureau: {bureau_name}
Assigned Cell: {cell_name}
Subject: {complaint.subject}
Description: {complaint.description}
Current Priority: {complaint.priority}
Current Status: {complaint.status}
SLA Deadline: {complaint.sla_due_at or 'Not calculated'}
Date Received: {complaint.date_received or complaint.created_at}

--- REQUIRED JSON OUTPUT FORMAT ---
{{
  "summary": "Concise 2-3 sentence institutional executive summary of the petition.",
  "main_issue": "Concise statement of the core regulatory or administrative contention.",
  "suggested_category": "Suggested category name (e.g. Fees, Faculty Shortage, Ragging, Unapproved Courses, etc.)",
  "suggested_department": "Suggested department or academic bureau.",
  "suggested_urgency": "High | Medium | Low",
  "facts": ["Fact 1 extracted from petition", "Fact 2 extracted from petition"],
  "missing_evidence": ["Missing document 1 required for adjudication", "Missing evidence 2"],
  "regulatory_concerns": ["Specific AICTE Approval Process Handbook (APH) guideline or regulation implicated"],
  "recommended_action": "Clear, decisive immediate next step for the investigating officer.",
  "action_rationale": "Clear administrative reasoning explaining why this next step is required at this lifecycle stage.",
  "action_checklist": [
    "1. Immediate action item for investigating officer",
    "2. Secondary procedural verification step",
    "3. Hearing / Show Cause notice requirement"
  ],
  "suggested_responsible_role": "Designated officer role (e.g. Section Head, Investigating Officer, Hearing Officer)",
  "followup_escalation": "Recommended follow-up threshold and timeline if institutional compliance is not achieved.",
  "potential_legal_concerns": "Any high-stakes judicial, RTI, or student safety concerns requiring human review, or 'Routine Regulatory Workflow' if none.",
  "confidence_score": 0.90
}}
"""

    raw_json, model_used = manager.generate_content_with_fallback(
        prompt=prompt,
        system_instruction=system_instruction,
        response_mime_type="application/json",
    )

    # Clean and parse JSON
    cleaned_json = raw_json.strip()
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.startswith("```"):
        cleaned_json = cleaned_json[3:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()

    data = json.loads(cleaned_json)

    with transaction.atomic():
        intel, created = AICaseIntelligence.objects.update_or_create(
            complaint=complaint,
            defaults={
                "summary": data.get("summary", ""),
                "main_issue": data.get("main_issue", complaint.subject[:250]),
                "relevant_institution": inst_name[:250],
                "relevant_department": data.get("suggested_department", "Administration")[:120],
                "relevant_bureau": bureau_name[:120],
                "relevant_cell": cell_name[:120],
                "important_facts": data.get("facts", []),
                "missing_evidence": data.get("missing_evidence", []),
                "suggested_urgency": data.get("suggested_urgency", "Medium")[:30],
                "regulatory_concerns": data.get("regulatory_concerns", []),
                "recommended_action": data.get("recommended_action", ""),
                "recommended_action_rationale": data.get("action_rationale", ""),
                "required_documents": data.get("missing_evidence", []),
                "suggested_responsible_role": data.get("suggested_responsible_role", f"Officer ({cell_name})")[:150],
                "action_checklist": data.get("action_checklist", []),
                "followup_escalation": data.get("followup_escalation", ""),
                "predicted_category": data.get("suggested_category", cat_name)[:100],
                "confidence_score": float(data.get("confidence_score", 0.90)),
                "is_rule_fallback": False,
                "model_name": f"Gemini ({model_used})",
            },
        )

        # Synchronize actionable checklist items
        checklist_items = data.get("action_checklist", [])
        if checklist_items:
            existing_actions = {a.recommendation_title: a for a in complaint.recommendation_actions.all()}
            for idx, item in enumerate(checklist_items):
                item_title = str(item).strip()
                if item_title not in existing_actions:
                    AIRecommendationAction.objects.create(
                        complaint=complaint,
                        recommendation_title=item_title,
                        action_state=AIRecommendationAction.ActionState.PENDING,
                    )

        # Evaluate legal review
        legal_obs = data.get("potential_legal_concerns", "")
        from apps.complaints.ai_service import assess_legal_attention
        legal_assess = assess_legal_attention(complaint)

        # If Gemini noted high legal/safety concern, update suggested reason
        if legal_obs and "routine" not in legal_obs.lower() and legal_assess["flag_level"] == "ROUTINE":
            legal_assess["flag_level"] = "PRIORITY"
            legal_assess["suggested_flag"] = "Priority AI Review"
            legal_assess["suggested_reason"] = f"Gemini Analysis flagged potential compliance/legal observation: '{legal_obs[:200]}'"

        LegalAttentionReview.objects.update_or_create(
            complaint=complaint,
            defaults={
                "flag_level": legal_assess["flag_level"],
                "suggested_flag": legal_assess["suggested_flag"],
                "suggested_reason": legal_assess["suggested_reason"],
                "evidence_excerpt": legal_assess.get("evidence_excerpt", "")[:500],
                "status": LegalAttentionReview.ReviewStatus.PENDING,
            },
        )

    return intel


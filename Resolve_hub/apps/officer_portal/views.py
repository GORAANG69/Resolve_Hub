from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.audit.services import log_action
from apps.complaints.models import Complaint
from apps.complaints.services import change_complaint_status
from apps.institutions.services import resolve_sla_hours

from .forms import OfficerStatusChangeForm, OfficerTriageOverrideForm
from .permissions import can_officer_access_complaint, get_officer_complaints_queryset, officer_required


def _safe_officer_summary(complaint: Complaint) -> dict:
    """
    Build a plain dictionary with STRICTLY non-identifying data.
    Never pass the Complaint ORM model directly to officer templates
    to eliminate any risk of accidental traversal into student PII.
    """
    inst = complaint.institution
    risk_info = None
    if inst and hasattr(inst, "risk_score"):
        risk_info = {
            "score": inst.risk_score.score,
            "band": inst.risk_score.band,
        }

    # AI Case Intelligence
    ai_intel = None
    if hasattr(complaint, "ai_intelligence") and complaint.ai_intelligence:
        ai_obj = complaint.ai_intelligence
        ai_intel = {
            "summary": ai_obj.summary,
            "main_issue": ai_obj.main_issue,
            "facts": ai_obj.facts or [],
            "missing_evidence": ai_obj.missing_evidence or [],
            "regulatory_concerns": ai_obj.regulatory_concerns or [],
            "recommended_action": ai_obj.recommended_action,
            "action_rationale": ai_obj.action_rationale,
            "confidence_score": round(ai_obj.confidence_score * 100, 1),
            "model_name": ai_obj.model_name,
            "recommendation_actions": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "action_type": a.action_type,
                    "priority": a.priority,
                    "status": a.status,
                    "status_display": a.get_status_display(),
                    "officer_notes": a.officer_notes,
                }
                for a in ai_obj.recommendation_actions.all()
            ],
        }

    # Legal Attention Review
    legal_rev = None
    if hasattr(complaint, "legal_review") and complaint.legal_review:
        lr_obj = complaint.legal_review
        legal_rev = {
            "flag_level": lr_obj.flag_level,
            "reason": lr_obj.reason,
            "evidence_excerpt": lr_obj.evidence_excerpt,
            "status": lr_obj.status,
            "review_notes": lr_obj.review_notes,
        }

    # Related Complaints (strictly scoped to same institution)
    related_list = []
    for rel in complaint.related_from.select_related("target_complaint", "target_complaint__category"):
        related_list.append({
            "complaint_code": rel.target_complaint.complaint_code,
            "subject": rel.target_complaint.subject,
            "category": rel.target_complaint.category.name if rel.target_complaint.category else "-",
            "status": rel.target_complaint.status,
            "priority": rel.target_complaint.priority,
            "relationship_type": rel.get_relationship_type_display(),
            "similarity_score": round(rel.similarity_score * 100, 1),
            "is_confirmed": rel.is_confirmed,
        })
    for rel in complaint.related_to.select_related("source_complaint", "source_complaint__category"):
        related_list.append({
            "complaint_code": rel.source_complaint.complaint_code,
            "subject": rel.source_complaint.subject,
            "category": rel.source_complaint.category.name if rel.source_complaint.category else "-",
            "status": rel.source_complaint.status,
            "priority": rel.source_complaint.priority,
            "relationship_type": rel.get_relationship_type_display(),
            "similarity_score": round(rel.similarity_score * 100, 1),
            "is_confirmed": rel.is_confirmed,
        })

    return {
        "id": complaint.id,
        "complaint_code": complaint.complaint_code,
        "category": complaint.category.name if complaint.category else "-",
        "institution_name": inst.name if inst else "Unassigned / General",
        "institution_aicte_id": inst.aicte_id if inst else "-",
        "institution_risk": risk_info,
        "cell": complaint.cell.name if complaint.cell else "-",
        "subject": complaint.subject,
        "description": complaint.description,
        "department_or_location": complaint.department_or_location,
        "student_urgency": complaint.student_urgency,
        "priority": complaint.priority,
        "source_channel": complaint.source_channel,
        "status": complaint.status,
        "lifecycle_stage": complaint.lifecycle_stage,
        "escalation_level": complaint.escalation_level,
        "sla_due_at": complaint.sla_due_at,
        "is_sla_breached": complaint.is_sla_breached,
        "sla_countdown": complaint.sla_countdown_info,
        "is_court_rti": complaint.is_court_rti,
        "court_rti_reference": complaint.court_rti_reference,
        "duplicate_of": complaint.duplicate_of.complaint_code if complaint.duplicate_of else None,
        "triage_confidence": complaint.triage_confidence,
        "triage_needs_review": complaint.triage_needs_review,
        "director_public_remark": complaint.director_public_remark,
        "hod_remark": complaint.hod_remark,
        "created_at": complaint.created_at,
        "ai_intelligence": ai_intel,
        "legal_review": legal_rev,
        "related_complaints": related_list,
        "status_history": [
            {
                "new_status": h.new_status,
                "created_at": h.created_at,
                "remark": h.remark,
                "changed_by": h.changed_by.role if h.changed_by else "System",
            }
            for h in complaint.status_history.all()
        ],
        "attachments": [
            {"id": a.id, "original_filename": a.original_filename}
            for a in complaint.attachments.all()
        ],
    }


@officer_required
def dashboard(request):
    qs = (
        get_officer_complaints_queryset(request.user)
        .select_related("category", "institution", "cell", "institution__risk_score")
        .order_by("-created_at")
    )
    summaries = [
        {
            "id": c.id,
            "complaint_code": c.complaint_code,
            "category": c.category.name if c.category else "-",
            "institution_name": c.institution.name if c.institution else "-",
            "cell": c.cell.name if c.cell else "-",
            "subject": c.subject,
            "priority": c.priority,
            "status": c.status,
            "lifecycle_stage": c.lifecycle_stage,
            "escalation_level": c.escalation_level,
            "is_sla_breached": c.is_sla_breached,
            "created_at": c.created_at,
        }
        for c in qs
    ]

    context = {
        "complaints": summaries,
        "officer_role": request.user.get_role_display(),
        "officer_cell": request.user.cell.name if request.user.cell else None,
        "officer_bureau": request.user.bureau.name if request.user.bureau else None,
    }
    return render(request, "officer_portal/dashboard.html", context)


@officer_required
def complaint_detail(request, pk: int):
    complaint = get_object_or_404(
        Complaint.objects.select_related(
            "category", "institution", "cell", "institution__risk_score",
            "ai_intelligence", "legal_review"
        ).prefetch_related(
            "ai_intelligence__recommendation_actions",
            "relationships_from__target_complaint__category",
            "relationships_to__source_complaint__category",
            "status_history",
            "attachments"
        ),
        pk=pk,
    )
    if not can_officer_access_complaint(request.user, complaint):
        raise PermissionDenied("You do not have permission to access complaints outside your cell/bureau.")

    status_form = OfficerStatusChangeForm(initial={"new_status": complaint.status})
    override_form = OfficerTriageOverrideForm(initial={"cell": complaint.cell, "priority": complaint.priority})

    if request.method == "POST":
        if "update_status" in request.POST:
            status_form = OfficerStatusChangeForm(request.POST)
            if status_form.is_valid():
                new_status = status_form.cleaned_data["new_status"]
                remark = status_form.cleaned_data.get("remark", "")
                try:
                    change_complaint_status(
                        complaint=complaint,
                        new_status=new_status,
                        actor=request.user,
                        remark=remark,
                    )
                    messages.success(request, f"Status updated to {new_status}.")
                    return redirect("officer_portal:complaint_detail", pk=pk)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))

        elif "override_triage" in request.POST:
            override_form = OfficerTriageOverrideForm(request.POST)
            if override_form.is_valid():
                old_cell = complaint.cell
                old_priority = complaint.priority
                new_cell = override_form.cleaned_data.get("cell") or old_cell
                new_priority = override_form.cleaned_data.get("priority") or old_priority
                reason = override_form.cleaned_data["override_reason"]

                complaint.cell = new_cell
                complaint.priority = new_priority
                complaint.triage_needs_review = False

                # Recompute SLA due at with new parameters
                sla_hours = resolve_sla_hours(new_cell, complaint.category, new_priority)
                complaint.sla_due_at = timezone.now() + timezone.timedelta(hours=sla_hours)
                complaint.save(update_fields=["cell", "priority", "triage_needs_review", "sla_due_at"])

                log_action(
                    actor=request.user,
                    action="TRIAGE_OVERRIDE",
                    target=f"complaint:{complaint.pk}",
                    metadata={
                        "old_cell": old_cell.name if old_cell else None,
                        "new_cell": new_cell.name if new_cell else None,
                        "old_priority": old_priority,
                        "new_priority": new_priority,
                        "reason": reason,
                    },
                )
                messages.success(request, "Triage parameters overridden and SLA recalculated.")
                return redirect("officer_portal:complaint_detail", pk=pk)

    return render(
        request,
        "officer_portal/complaint_detail.html",
        {
            "complaint": _safe_officer_summary(complaint),
            "status_form": status_form,
            "override_form": override_form,
        },
    )

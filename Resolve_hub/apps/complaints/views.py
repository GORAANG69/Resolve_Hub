import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.officer_portal.permissions import can_officer_access_complaint
from .forms import (
    AttachmentUploadForm,
    ComplaintForm,
    LetterOCRUploadForm,
    OfficialMatterForm,
)
from .models import Attachment, Complaint, SourceChannel, Status
from .ocr import extract_text_from_file
from .services import (
    compute_contact_hash,
    get_system_intake_user,
    register_complaint,
)
from .storage import (
    AttachmentValidationError,
    get_authorized_file_url,
    save_attachment_file,
)


@login_required
def dashboard(request):
    complaints = Complaint.objects.filter(student=request.user)
    counts = {
        "total": complaints.count(),
        "submitted": complaints.filter(status=Status.SUBMITTED).count(),
        "under_review": complaints.filter(status=Status.UNDER_REVIEW).count(),
        "in_progress": complaints.filter(status=Status.IN_PROGRESS).count(),
        "resolved": complaints.filter(status=Status.RESOLVED).count(),
    }
    recent = complaints[:5]
    return render(request, "complaints/dashboard.html", {"counts": counts, "recent": recent})


@login_required
def complaint_list(request):
    complaints = Complaint.objects.filter(student=request.user).select_related("category", "institution", "cell")
    status_filter = request.GET.get("status")
    if status_filter in dict(Status.choices):
        complaints = complaints.filter(status=status_filter)
    return render(
        request,
        "complaints/list.html",
        {"complaints": complaints, "statuses": Status.choices, "status_filter": status_filter},
    )


@login_required
def complaint_create(request):
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = register_complaint(
                submitting_user=request.user,
                institution=form.cleaned_data.get("institution"),
                category=form.cleaned_data["category"],
                subject=form.cleaned_data["subject"],
                description=form.cleaned_data["description"],
                department_or_location=form.cleaned_data.get("department_or_location", ""),
                student_urgency=form.cleaned_data.get("student_urgency", "MEDIUM"),
                is_court_rti=form.cleaned_data.get("is_court_rti", False),
                court_rti_reference=form.cleaned_data.get("court_rti_reference", ""),
                is_confidential=form.cleaned_data.get("is_confidential", False),
                source_channel=SourceChannel.WEB,
                consent_given=form.cleaned_data.get("dpdp_consent", True),
            )
            messages.success(request, f"Grievance {complaint.complaint_code} successfully registered.")
            return redirect("complaints:detail", public_id=complaint.complaint_code)
    else:
        form = ComplaintForm()
    return render(request, "complaints/create.html", {"form": form})


@login_required
def complaint_detail(request, public_id):
    complaint = get_object_or_404(
        Complaint.objects.select_related("category", "institution", "cell").prefetch_related("status_history", "attachments"),
        complaint_code=public_id,
        student=request.user,
    )
    upload_form = AttachmentUploadForm()
    return render(request, "complaints/detail.html", {"complaint": complaint, "upload_form": upload_form})


@login_required
def attachment_upload(request, public_id):
    complaint = get_object_or_404(Complaint, complaint_code=public_id, student=request.user)

    if request.method == "POST":
        form = AttachmentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            try:
                storage_path = save_attachment_file(complaint, uploaded_file)
            except AttachmentValidationError as exc:
                messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
                return redirect("complaints:detail", public_id=public_id)

            Attachment.objects.create(
                complaint=complaint,
                storage_path=storage_path,
                original_filename=uploaded_file.name,
                content_type=uploaded_file.content_type,
                size_bytes=uploaded_file.size,
            )
            messages.success(request, "Attachment uploaded.")
        else:
            messages.error(request, "Please choose a valid file.")
    return redirect("complaints:detail", public_id=public_id)


@login_required
def attachment_download(request, attachment_id):
    attachment = get_object_or_404(Attachment.objects.select_related("complaint", "complaint__cell"), pk=attachment_id)
    complaint = attachment.complaint

    is_owner = complaint.student_id == request.user.id
    is_director_or_admin = request.user.is_director or request.user.is_admin_role
    is_authorized_officer = can_officer_access_complaint(request.user, complaint)

    if not (is_owner or is_director_or_admin or is_authorized_officer):
        raise PermissionDenied("You do not have access to this attachment.")

    url = get_authorized_file_url(attachment)
    return redirect(url)


# ---------------------------------------------------------------------------
# Section 8: Public Status Tracker (/track/)
# ---------------------------------------------------------------------------
def public_tracker(request):
    """
    Public lookup portal: requires case ID + matching email/mobile.
    Rate limited per IP.
    Returns STRICTLY safe non-identifying fields:
    Status, lifecycle stage, institution name, cell, last updated, public remark.
    NEVER leaks complainant PII, internal notes, attachments, or spam analysis.
    """
    ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    rate_limit_key = f"rate_limit_track_{ip}"
    attempts = cache.get(rate_limit_key, 0)

    result = None
    error_message = None

    if request.method == "POST":
        if attempts >= 10:
            error_message = "Too many tracking attempts. Please wait an hour before trying again."
        else:
            cache.set(rate_limit_key, attempts + 1, timeout=3600)
            case_id = request.POST.get("case_id", "").strip().upper()
            contact = request.POST.get("contact", "").strip().lower()

            if not case_id or not contact:
                error_message = "Please enter both Case ID and your registered email or mobile."
            else:
                complaint = (
                    Complaint.objects.select_related("institution", "cell", "student")
                    .filter(complaint_code=case_id)
                    .first()
                )

                valid_match = False
                if complaint:
                    # Compare contact securely (email, mobile, or salted hash)
                    student_email = (complaint.student.email or "").strip().lower()
                    student_mobile = (complaint.student.mobile_number or "").strip()
                    supplied_hash = compute_contact_hash(contact)

                    if (
                        secrets.compare_digest(student_email, contact)
                        or (student_mobile and secrets.compare_digest(student_mobile, contact))
                        or (complaint.complainant_contact_hash and secrets.compare_digest(complaint.complainant_contact_hash, supplied_hash))
                    ):
                        valid_match = True

                if valid_match and complaint:
                    # Strictly construct plain dictionary of permitted public fields
                    result = {
                        "case_id": complaint.complaint_code,
                        "status": complaint.get_status_display(),
                        "lifecycle_stage": complaint.lifecycle_stage,
                        "institution_name": complaint.institution.name if complaint.institution else "General",
                        "cell_name": complaint.cell.name if complaint.cell else "PGRC",
                        "last_updated": complaint.updated_at,
                        "public_remark": complaint.director_public_remark or "Under processing by assigned AICTE cell.",
                    }
                else:
                    error_message = "No complaint found matching the provided Case ID and contact details."

    return render(
        request,
        "complaints/tracker.html",
        {
            "result": result,
            "error_message": error_message,
        },
    )


# ---------------------------------------------------------------------------
# Section 3: Letter OCR Upload (/complaints/ocr/)
# ---------------------------------------------------------------------------
@login_required
def ocr_intake_view(request):
    """
    Staff/officer upload portal for scanned physical grievances.
    """
    if not (request.user.is_officer or request.user.is_staff or request.user.is_admin_role):
        raise PermissionDenied("Officer or administrative access required for OCR intake.")

    if request.method == "POST":
        form = LetterOCRUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            institution = form.cleaned_data.get("institution")
            sender_name = form.cleaned_data.get("complainant_name") or "Physical Letter Complainant"
            sender_contact = form.cleaned_data.get("complainant_contact") or ""

            extracted_text, is_success = extract_text_from_file(uploaded_file, uploaded_file.name)
            subject = f"Scanned Letter Grievance - {uploaded_file.name}"

            complaint = register_complaint(
                submitting_user=get_system_intake_user(),
                institution=institution,
                subject=subject[:200],
                description=extracted_text,
                source_channel=SourceChannel.LETTER_OCR,
                consent_given=True,
            )

            # Store original scanned file as private attachment
            try:
                storage_path = save_attachment_file(complaint, uploaded_file)
                Attachment.objects.create(
                    complaint=complaint,
                    storage_path=storage_path,
                    original_filename=uploaded_file.name,
                    content_type=uploaded_file.content_type,
                    size_bytes=uploaded_file.size,
                )
            except Exception as e:
                pass

            messages.success(request, f"OCR Letter registered as Case {complaint.complaint_code}.")
            return redirect("officer_portal:complaint_detail", pk=complaint.pk)
    else:
        form = LetterOCRUploadForm()

    return render(request, "complaints/ocr_upload.html", {"form": form})


# ---------------------------------------------------------------------------
# Section 3: Court / RTI / Parliament Intake (/complaints/official/)
# ---------------------------------------------------------------------------
@login_required
def official_matter_create_view(request):
    """
    Officer-facing registration for Court, RTI, or Parliamentary matters.
    """
    if not (request.user.is_officer or request.user.is_director or request.user.is_admin_role):
        raise PermissionDenied("Officer access required to register official matters.")

    if request.method == "POST":
        form = OfficialMatterForm(request.POST)
        if form.is_valid():
            complaint = register_complaint(
                submitting_user=request.user,
                institution=form.cleaned_data.get("institution"),
                subject=form.cleaned_data["subject"],
                description=form.cleaned_data["description"],
                source_channel=form.cleaned_data["source_channel"],
                is_court_rti=True,
                court_rti_reference=form.cleaned_data["court_rti_reference"],
                consent_given=True,
            )
            messages.success(
                request,
                f"Official matter {complaint.complaint_code} registered under Legal / Compliance routing.",
            )
            return redirect("officer_portal:complaint_detail", pk=complaint.pk)
    else:
        form = OfficialMatterForm()

    return render(request, "complaints/official_matter_create.html", {"form": form})

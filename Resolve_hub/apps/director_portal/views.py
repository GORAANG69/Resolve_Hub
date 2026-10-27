from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Avg, Case, Count, DurationField, ExpressionWrapper, F, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.complaints.models import Complaint, ComplaintCategory, PriorityLevel, SpamClassification, Status
from apps.complaints.services import change_complaint_status, forward_complaint_to_department
from .analytics import compute_institutional_analytics
from .forms import DirectorRemarkForm, ForwardToDepartmentForm, StatusChangeForm
from .permissions import director_required


@director_required
def dashboard(request):
    complaints = Complaint.objects.all()
    counts = {
        "total": complaints.count(),
        "submitted": complaints.filter(status=Status.SUBMITTED).count(),
        "under_review": complaints.filter(status=Status.UNDER_REVIEW).count(),
        "in_progress": complaints.filter(status=Status.IN_PROGRESS).count(),
        "resolved": complaints.filter(status=Status.RESOLVED).count(),
        "suspected_spam": complaints.filter(
            spam_classification__in=[SpamClassification.REVIEW, SpamClassification.SUSPICIOUS]
        ).count(),
    }
    recent = complaints.select_related("student", "category")[:8]
    return render(request, "director_portal/dashboard.html", {"counts": counts, "recent": recent})


@director_required
def complaint_list(request):
    complaints = Complaint.objects.select_related("student", "category", "institution").all()

    code = request.GET.get("code", "").strip()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "").strip()
    institution_id = request.GET.get("institution", "").strip()
    spam_classification = request.GET.get("spam_classification", "")
    order = request.GET.get("order", "urgent").strip()

    if code:
        complaints = complaints.filter(complaint_code__icontains=code)
    if query:
        complaints = complaints.filter(
            Q(student__full_name__icontains=query)
            | Q(student__roll_number__icontains=query)
            | Q(institution__name__icontains=query)
        )
    if category:
        complaints = complaints.filter(category__slug=category)
    if status in dict(Status.choices):
        complaints = complaints.filter(status=status)
    if priority in dict(PriorityLevel.choices):
        complaints = complaints.filter(priority=priority)
    if institution_id and institution_id.isdigit():
        complaints = complaints.filter(institution_id=int(institution_id))
    if spam_classification in dict(SpamClassification.choices):
        complaints = complaints.filter(spam_classification=spam_classification)

    # Urgent-first ordering by priority (Critical -> High -> Medium -> Low), then creation date
    priority_ranking = Case(
        When(priority=PriorityLevel.CRITICAL, then=Value(1)),
        When(priority=PriorityLevel.HIGH, then=Value(2)),
        When(priority=PriorityLevel.MEDIUM, then=Value(3)),
        When(priority=PriorityLevel.LOW, then=Value(4)),
        default=Value(5),
        output_field=IntegerField(),
    )
    if order == "date":
        complaints = complaints.order_by("-created_at")
    else:
        complaints = complaints.order_by(priority_ranking, "-created_at")

    context = {
        "complaints": complaints[:200],
        "categories": ComplaintCategory.objects.filter(is_active=True),
        "statuses": Status.choices,
        "priorities": PriorityLevel.choices,
        "spam_classifications": SpamClassification.choices,
        "filters": {
            "code": code,
            "q": query,
            "category": category,
            "status": status,
            "priority": priority,
            "institution": institution_id,
            "spam_classification": spam_classification,
            "order": order,
        },
    }
    return render(request, "director_portal/complaint_list.html", context)


@director_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(
        Complaint.objects.select_related("student", "category").prefetch_related(
            "status_history", "attachments", "spam_analysis"
        ),
        pk=pk,
    )

    status_form = StatusChangeForm(initial={"new_status": complaint.status})
    remark_form = DirectorRemarkForm(instance=complaint)
    forward_form = ForwardToDepartmentForm(initial={"department": complaint.assigned_department})

    if request.method == "POST":
        if "forward_complaint" in request.POST:
            forward_form = ForwardToDepartmentForm(request.POST)
            if forward_form.is_valid():
                forward_complaint_to_department(
                    complaint=complaint,
                    department=forward_form.cleaned_data["department"],
                    actor=request.user,
                )
                messages.success(
                    request,
                    f"Forwarded to the {forward_form.cleaned_data['department']} HOD. "
                    "Student identity is not shared with the HOD.",
                )
                return redirect("director_portal:complaint_detail", pk=pk)
        elif "change_status" in request.POST:
            status_form = StatusChangeForm(request.POST)
            if status_form.is_valid():
                try:
                    change_complaint_status(
                        complaint=complaint,
                        new_status=status_form.cleaned_data["new_status"],
                        actor=request.user,
                        remark=status_form.cleaned_data["remark"],
                    )
                    messages.success(request, "Status updated.")
                    return redirect("director_portal:complaint_detail", pk=pk)
                except ValidationError as exc:
                    status_form.add_error(None, exc.message if hasattr(exc, "message") else str(exc))
        elif "save_remarks" in request.POST:
            remark_form = DirectorRemarkForm(request.POST, instance=complaint)
            if remark_form.is_valid():
                remark_form.save()
                messages.success(request, "Remarks saved.")
                return redirect("director_portal:complaint_detail", pk=pk)

    return render(
        request,
        "director_portal/complaint_detail.html",
        {
            "complaint": complaint,
            "status_form": status_form,
            "remark_form": remark_form,
            "forward_form": forward_form,
        },
    )


@director_required
def spam_review(request):
    complaints = (
        Complaint.objects.select_related("student", "category", "spam_analysis")
        .filter(spam_classification__in=[SpamClassification.REVIEW, SpamClassification.SUSPICIOUS])
        .order_by("-spam_score", "-created_at")
    )
    return render(request, "director_portal/spam_review.html", {"complaints": complaints})


@director_required
def analytics(request):
    """
    Institutional Complaint Trend Analysis & Comprehensive Metrics.
    Aggregates real complaint records by institution, category, priority, status, and velocity.
    """
    context = compute_institutional_analytics(request.GET.dict())
    return render(request, "director_portal/analytics.html", context)


# Direct alias for consistent institutional analytics routing
institutional_analytics = analytics

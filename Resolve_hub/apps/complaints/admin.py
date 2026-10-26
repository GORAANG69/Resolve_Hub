from django.contrib import admin

from .models import (
    Attachment,
    CategoryCellRoute,
    Complaint,
    ComplaintCategory,
    ComplaintStatusHistory,
    EscalationEvent,
)


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CategoryCellRoute)
class CategoryCellRouteAdmin(admin.ModelAdmin):
    list_display = ("category", "cell")


@admin.register(EscalationEvent)
class EscalationEventAdmin(admin.ModelAdmin):
    list_display = ("complaint", "level", "triggered_at", "notified_user", "channel")
    list_filter = ("level", "channel")


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ("storage_path", "original_filename", "content_type", "size_bytes", "uploaded_at")


class StatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "remark", "created_at")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "complaint_code",
        "student",
        "institution",
        "cell",
        "priority",
        "status",
        "escalation_level",
        "spam_classification",
        "created_at",
    )
    list_filter = ("status", "priority", "escalation_level", "cell", "category", "is_court_rti")
    search_fields = ("complaint_code", "subject", "student__email", "institution__name", "institution__aicte_id")
    readonly_fields = ("complaint_code", "spam_score", "spam_classification", "created_at", "updated_at")
    inlines = [AttachmentInline, StatusHistoryInline]

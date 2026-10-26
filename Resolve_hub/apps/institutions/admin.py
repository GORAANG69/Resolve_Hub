from django.contrib import admin
from .models import Institution, Bureau, Cell, SLAPolicy, InstitutionRiskScore


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("aicte_id", "name", "state", "district", "institution_type", "is_active")
    list_filter = ("institution_type", "state", "is_active")
    search_fields = ("aicte_id", "name", "state", "district")


@admin.register(Bureau)
class BureauAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("name", "bureau", "slug", "default_sla_hours", "is_active")
    list_filter = ("bureau", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ("cell", "category", "priority", "sla_hours")
    list_filter = ("cell", "priority")


@admin.register(InstitutionRiskScore)
class InstitutionRiskScoreAdmin(admin.ModelAdmin):
    list_display = ("institution", "score", "band", "computed_at")
    list_filter = ("band",)
    search_fields = ("institution__name", "institution__aicte_id")

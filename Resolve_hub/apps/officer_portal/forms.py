from django import forms
from apps.complaints.models import PriorityLevel, Status
from apps.complaints.widgets import bootstrapify
from apps.institutions.models import Cell


class OfficerStatusChangeForm(forms.Form):
    new_status = forms.ChoiceField(
        choices=[
            (Status.UNDER_REVIEW, "Under review"),
            (Status.IN_PROGRESS, "In progress"),
            (Status.AWAITING_COMPLAINANT, "Awaiting Complainant response"),
            (Status.RESOLVED, "Resolved"),
            (Status.CLOSED, "Closed"),
            (Status.REJECTED, "Rejected"),
        ],
        label="Update status",
    )
    remark = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Public remark explaining this update..."}),
        required=False,
        label="Public remark",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)


class OfficerTriageOverrideForm(forms.Form):
    """
    Allows authorized officers to override cell or priority assignment with human-in-the-loop review.
    """
    cell = forms.ModelChoiceField(queryset=Cell.objects.filter(is_active=True), required=False, label="Reassign Cell")
    priority = forms.ChoiceField(choices=PriorityLevel.choices, required=False, label="Change Priority")
    override_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Reason for override..."}),
        required=True,
        label="Reason for override",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)

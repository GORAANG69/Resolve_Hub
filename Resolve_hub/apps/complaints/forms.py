from django import forms
from django.core.exceptions import ValidationError

from apps.institutions.models import Institution
from .models import Attachment, Complaint, ComplaintCategory, PriorityLevel, SourceChannel
from .widgets import bootstrapify


class AttachmentUploadForm(forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)


class ComplaintForm(forms.ModelForm):
    """
    Public complainant form for registering grievances against institutions.
    Enforces DPDP consent and institution selection.
    """

    institution = forms.ModelChoiceField(
        queryset=Institution.objects.filter(is_active=True),
        required=False,
        empty_label="Select Institution (or leave blank if not listed)",
        label="Technical Institution",
    )
    is_court_rti = forms.BooleanField(
        required=False,
        label="This grievance involves an active Court or RTI reference",
    )
    court_rti_reference = forms.CharField(
        required=False,
        max_length=100,
        label="Court / RTI Case Number (if applicable)",
    )
    dpdp_consent = forms.BooleanField(
        required=True,
        initial=True,
        label="I consent to the collection and processing of my grievance details under DPDP Act 2023.",
    )

    class Meta:
        model = Complaint
        fields = [
            "institution",
            "category",
            "subject",
            "description",
            "department_or_location",
            "student_urgency",
            "is_court_rti",
            "court_rti_reference",
            "is_confidential",
            "dpdp_consent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "Describe your grievance in detail..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Select a category"
        bootstrapify(self)


class LetterOCRUploadForm(forms.Form):
    """
    Staff-only upload form for scanned grievance letters.
    """

    file = forms.FileField(label="Scanned Letter / Evidence (PDF, PNG, JPG)")
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.filter(is_active=True),
        required=False,
        empty_label="Select Institution (optional)",
    )
    complainant_name = forms.CharField(required=False, label="Sender / Complainant Name")
    complainant_contact = forms.CharField(required=False, label="Sender Email or Mobile")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)


class OfficialMatterForm(forms.Form):
    """
    Officer form for logging Court, RTI, or Parliamentary matters directly into Legal Cell.
    """

    source_channel = forms.ChoiceField(
        choices=[
            (SourceChannel.COURT, "Court Case"),
            (SourceChannel.RTI, "RTI Application"),
            (SourceChannel.PARLIAMENT, "Parliament Question"),
        ],
        label="Channel",
    )
    court_rti_reference = forms.CharField(
        max_length=100,
        required=True,
        label="Reference / Diary Number",
    )
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.filter(is_active=True),
        required=False,
        empty_label="Select Institution (optional)",
    )
    subject = forms.CharField(max_length=200, label="Matter Subject")
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        label="Matter Details / Brief",
    )
    priority = forms.ChoiceField(
        choices=PriorityLevel.choices,
        initial=PriorityLevel.HIGH,
        label="Initial Priority",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)

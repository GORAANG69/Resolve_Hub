from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.complaints.widgets import bootstrapify

from .models import ComplainantType, Role, User


def _reclaimable_unverified(**lookup):
    """
    An account that was registered but never OTP-verified is a placeholder,
    not a real account. After REGISTRATION_UNVERIFIED_TTL_HOURS it stops
    blocking that email/roll number so a genuine user isn't locked out
    forever by someone else's abandoned (or malicious) signup attempt.

    Returns the reclaimable User, or None.
    """
    cutoff = timezone.now() - timedelta(hours=settings.REGISTRATION_UNVERIFIED_TTL_HOURS)
    return User.objects.filter(is_active=False, date_joined__lt=cutoff, **lookup).first()


class StudentRegistrationForm(forms.ModelForm):
    """
    Public registration form for Complainants (Students, Faculty, Public).
    Deliberately excludes officer roles, `is_staff`, `is_superuser`, and
    any permission field - registration ALWAYS creates a STUDENT/Complainant role.

    Roll number is strictly required for Students, but optional for Faculty/Public.
    Requires DPDP consent checkbox to proceed.
    """

    complainant_type = forms.ChoiceField(
        choices=ComplainantType.choices,
        initial=ComplainantType.STUDENT,
        label="I am registering as",
    )
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, min_length=8)
    dpdp_consent = forms.BooleanField(
        required=True,
        initial=True,
        label="I consent to the collection and processing of my details for grievance redressal under DPDP Act.",
    )

    class Meta:
        model = User
        fields = [
            "complainant_type",
            "full_name",
            "roll_number",
            "email",
            "mobile_number",
            "course",
            "branch",
            "semester",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Roll number optional at field level; enforced in clean() for students
        self.fields["roll_number"].required = False
        bootstrapify(self)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = User.objects.filter(email=email).first()
        if existing:
            if existing.is_active:
                raise ValidationError("An account with this email already exists.")
            if not _reclaimable_unverified(email=email):
                raise ValidationError(
                    "This email already has a registration awaiting verification. "
                    "Check your inbox for the code, or try again later."
                )
        return email

    def clean_roll_number(self):
        roll_number = (self.cleaned_data.get("roll_number") or "").strip()
        if roll_number:
            existing = User.objects.filter(roll_number=roll_number).first()
            if existing:
                if existing.is_active:
                    raise ValidationError("An account with this roll number already exists.")
                if not _reclaimable_unverified(roll_number=roll_number):
                    raise ValidationError(
                        "This roll number already has a registration awaiting verification. "
                        "Check your inbox for the code, or try again later."
                    )
        return roll_number or None

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        ctype = cleaned.get("complainant_type")
        roll = cleaned.get("roll_number")
        if ctype == ComplainantType.STUDENT and not roll:
            self.add_error("roll_number", "Roll number is required for student registration.")

        return cleaned

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        roll_number = self.cleaned_data.get("roll_number")

        delete_filter = Q(email=email)
        if roll_number:
            delete_filter |= Q(roll_number=roll_number)

        User.objects.filter(is_active=False).filter(delete_filter).delete()

        user = super().save(commit=False)
        user.role = Role.STUDENT
        user.username = user.email
        user.is_staff = False
        user.is_superuser = False
        user.is_active = False
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# Alias for clarity
ComplainantRegistrationForm = StudentRegistrationForm


class EmailLoginForm(AuthenticationForm):
    """
    Standard Django auth form, but label the username field 'Email' to match
    the custom User model's USERNAME_FIELD.
    """

    username = forms.EmailField(label="Email", max_length=254)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autofocus": True, "placeholder": "you@example.com"}
        )
        bootstrapify(self)


class OTPVerifyForm(forms.Form):
    """
    Verifies the numeric code texted/emailed to the user.
    """

    code = forms.CharField(max_length=8, min_length=4, label="Verification code")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrapify(self)

    def clean_code(self):
        return self.cleaned_data["code"].strip()

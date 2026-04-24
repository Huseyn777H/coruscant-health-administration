from cryptography.fernet import Fernet
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import (
    DoctorProfile,
    DoctorReport,
    EmergencyIntake,
    HealthReading,
    OrderResult,
    PatientRecord,
    SecureDocument,
    ServiceOrder,
    User,
    UserRole,
)


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))


class RegistrationForm(UserCreationForm):
    specialty = forms.CharField(required=False)
    license_id = forms.CharField(required=False, label="Medical license ID")
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    emergency_contact = forms.CharField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "role",
            "phone_number",
            "district",
            "device_identifier",
        )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        specialty = cleaned_data.get("specialty")
        license_id = cleaned_data.get("license_id")
        if role == UserRole.DOCTOR and (not specialty or not license_id):
            raise forms.ValidationError("Doctors must provide a specialty and license ID.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = user.role in {UserRole.EMERGENCY, UserRole.DEPARTMENT}
        if commit:
            user.save()
            if user.role == UserRole.PATIENT:
                PatientRecord.objects.create(
                    patient=user,
                    date_of_birth=self.cleaned_data.get("date_of_birth"),
                    emergency_contact=self.cleaned_data.get("emergency_contact", ""),
                )
            if user.role == UserRole.DOCTOR:
                DoctorProfile.objects.create(
                    doctor=user,
                    specialty=self.cleaned_data["specialty"],
                    license_id=self.cleaned_data["license_id"],
                )
        return user


class HealthReadingForm(forms.ModelForm):
    recorded_at = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = HealthReading
        fields = (
            "recorded_at",
            "heart_rate",
            "blood_oxygen",
            "temperature_c",
            "systolic_bp",
            "diastolic_bp",
            "symptoms",
        )


class DoctorReportForm(forms.ModelForm):
    class Meta:
        model = DoctorReport
        fields = ("patient", "trend", "report_title", "summary", "prescription")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = User.objects.filter(
            role=UserRole.PATIENT,
            is_approved=True,
        )


class ServiceOrderForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = ("patient", "department", "service_type", "notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = User.objects.filter(
            role=UserRole.PATIENT,
            is_approved=True,
        )
        self.fields["department"].queryset = User.objects.filter(
            role=UserRole.DEPARTMENT,
            is_approved=True,
        )
        self.fields["department"].required = False


class OrderResultForm(forms.ModelForm):
    class Meta:
        model = OrderResult
        fields = ("findings",)


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("is_approved",)


class EmergencyIntakeForm(forms.ModelForm):
    class Meta:
        model = EmergencyIntake
        fields = ("full_name", "age", "triage_level", "symptoms")


class SecureDocumentForm(forms.Form):
    owner = forms.ModelChoiceField(queryset=User.objects.none())
    category = forms.ChoiceField(choices=SecureDocument._meta.get_field("category").choices)
    title = forms.CharField(max_length=160)
    document = forms.FileField()

    def __init__(self, *args, **kwargs):
        owner_queryset = kwargs.pop("owner_queryset", User.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = owner_queryset

    def save(self, uploaded_by):
        upload = self.cleaned_data["document"]
        cipher = Fernet(settings.DOCUMENT_ENCRYPTION_KEY.encode())
        encrypted_payload = cipher.encrypt(upload.read())
        return SecureDocument.objects.create(
            owner=self.cleaned_data["owner"],
            uploaded_by=uploaded_by,
            category=self.cleaned_data["category"],
            title=self.cleaned_data["title"],
            original_filename=upload.name,
            content_type=getattr(upload, "content_type", "") or "application/octet-stream",
            encrypted_payload=encrypted_payload,
        )

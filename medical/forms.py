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
    specialty = forms.CharField(required=False, widget=forms.TextInput(attrs={"maxlength": 120}))
    license_id = forms.CharField(
        required=False,
        label="Medical license ID",
        widget=forms.TextInput(attrs={"maxlength": 120}),
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    emergency_contact = forms.CharField(required=False, widget=forms.TextInput(attrs={"maxlength": 160}))

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update({"maxlength": 150})
        self.fields["last_name"].widget.attrs.update({"maxlength": 150})
        self.fields["username"].widget.attrs.update({"maxlength": 150})
        self.fields["email"].widget.attrs.update({"type": "email"})
        self.fields["phone_number"].widget.attrs.update({"maxlength": 32})
        self.fields["district"].widget.attrs.update({"maxlength": 120})
        self.fields["device_identifier"].widget.attrs.update({"maxlength": 120})

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
        widgets = {
            "heart_rate": forms.NumberInput(attrs={"min": 20, "max": 240}),
            "blood_oxygen": forms.NumberInput(attrs={"min": 50, "max": 100}),
            "temperature_c": forms.NumberInput(attrs={"min": 30, "max": 45, "step": 0.1}),
            "systolic_bp": forms.NumberInput(attrs={"min": 60, "max": 260}),
            "diastolic_bp": forms.NumberInput(attrs={"min": 30, "max": 160}),
            "symptoms": forms.Textarea(attrs={"maxlength": 1000}),
        }


class DoctorReportForm(forms.ModelForm):
    class Meta:
        model = DoctorReport
        fields = ("patient", "trend", "report_title", "summary", "prescription")
        widgets = {
            "report_title": forms.TextInput(attrs={"maxlength": 160}),
            "summary": forms.Textarea(attrs={"maxlength": 2000}),
            "prescription": forms.Textarea(attrs={"maxlength": 2000}),
        }

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
        widgets = {
            "notes": forms.Textarea(attrs={"maxlength": 2000}),
        }

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
        widgets = {
            "findings": forms.Textarea(attrs={"maxlength": 2000}),
        }


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("is_approved",)


class EmergencyIntakeForm(forms.ModelForm):
    class Meta:
        model = EmergencyIntake
        fields = ("full_name", "age", "triage_level", "symptoms")
        widgets = {
            "full_name": forms.TextInput(attrs={"maxlength": 160}),
            "age": forms.NumberInput(attrs={"min": 0, "max": 130}),
            "triage_level": forms.TextInput(attrs={"maxlength": 80}),
            "symptoms": forms.Textarea(attrs={"maxlength": 2000}),
        }


class SecureDocumentForm(forms.Form):
    owner = forms.ModelChoiceField(queryset=User.objects.none())
    category = forms.ChoiceField(choices=SecureDocument._meta.get_field("category").choices)
    title = forms.CharField(max_length=160, widget=forms.TextInput(attrs={"maxlength": 160}))
    document = forms.FileField(widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"}))

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

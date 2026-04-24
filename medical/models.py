from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    PATIENT = "patient", "Patient"
    DOCTOR = "doctor", "Doctor"
    ADMINISTRATOR = "administrator", "Administrator"
    DEPARTMENT = "department", "Department"
    EMERGENCY = "emergency", "Emergency Services"


class TrendChoice(models.TextChoices):
    IMPROVING = "improving", "Improving"
    STABLE = "stable", "Stable"
    ATTENTION = "attention", "Needs Attention"


class ServiceStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class ServiceType(models.TextChoices):
    CT_SCAN = "ct_scan", "CT Scan"
    PET_SCAN = "pet_scan", "PET Scan"
    MRI = "mri", "MRI"
    LAB_PANEL = "lab_panel", "Lab Panel"
    ULTRASOUND = "ultrasound", "Ultrasound"


class DocumentCategory(models.TextChoices):
    CLINICAL = "clinical", "Clinical Document"
    IDENTITY = "identity", "Identity / Registration"
    IMAGING = "imaging", "Imaging Result"
    LAB = "lab", "Lab Result"
    OTHER = "other", "Other"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices)
    is_approved = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=32, blank=True)
    district = models.CharField(max_length=120, blank=True)
    device_identifier = models.CharField(max_length=120, blank=True)

    def save(self, *args, **kwargs):
        if self.role == UserRole.ADMINISTRATOR:
            self.is_approved = True
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    @property
    def full_display_name(self):
        full_name = self.get_full_name().strip()
        return full_name or self.username


class PatientRecord(models.Model):
    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_record",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=160, blank=True)
    medical_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Patient record for {self.patient.full_display_name}"


class DoctorProfile(models.Model):
    doctor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    specialty = models.CharField(max_length=120)
    license_id = models.CharField(max_length=120)

    def __str__(self):
        return f"{self.doctor.full_display_name} ({self.specialty})"


class HealthReading(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_readings",
    )
    recorded_at = models.DateTimeField(default=timezone.now)
    heart_rate = models.PositiveIntegerField(
        validators=[MinValueValidator(20), MaxValueValidator(240)]
    )
    blood_oxygen = models.PositiveIntegerField(
        validators=[MinValueValidator(50), MaxValueValidator(100)]
    )
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1)
    systolic_bp = models.PositiveIntegerField(
        validators=[MinValueValidator(60), MaxValueValidator(260)]
    )
    diastolic_bp = models.PositiveIntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(160)]
    )
    symptoms = models.TextField(blank=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient.full_display_name} reading at {self.recorded_at:%Y-%m-%d %H:%M}"


class DoctorReport(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_reports",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="written_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    trend = models.CharField(max_length=20, choices=TrendChoice.choices)
    report_title = models.CharField(max_length=160)
    summary = models.TextField()
    prescription = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.report_title} for {self.patient.full_display_name}"


class ServiceOrder(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_orders",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issued_service_orders",
    )
    department = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )
    service_type = models.CharField(max_length=40, choices=ServiceType.choices)
    status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        default=ServiceStatus.REQUESTED,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_service_type_display()} for {self.patient.full_display_name}"

    @property
    def has_result(self):
        return hasattr(self, "result")


class OrderResult(models.Model):
    order = models.OneToOneField(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="result",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_order_results",
    )
    findings = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for order #{self.order_id}"


class SecureDocument(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    category = models.CharField(max_length=20, choices=DocumentCategory.choices)
    title = models.CharField(max_length=160)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    encrypted_payload = models.BinaryField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class EmergencyIntake(models.Model):
    full_name = models.CharField(max_length=160)
    age = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(130)])
    triage_level = models.CharField(max_length=80)
    symptoms = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_intakes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.triage_level})"

# Create your models here.

from django.core.management.base import BaseCommand
from django.utils import timezone

from medical.models import (
    DoctorProfile,
    DoctorReport,
    HealthReading,
    PatientRecord,
    SecureDocument,
    ServiceOrder,
    ServiceStatus,
    User,
    UserRole,
)
from medical.services import encrypt_bytes


class Command(BaseCommand):
    help = "Create demo accounts and sample records for submission review."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="cha_admin",
            defaults={
                "first_name": "Medxec",
                "last_name": "Onuta",
                "email": "admin@coruscant-health.local",
                "role": UserRole.ADMINISTRATOR,
            },
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()

        patient, created = User.objects.get_or_create(
            username="patient_demo",
            defaults={
                "first_name": "Lira",
                "last_name": "Venn",
                "email": "patient@coruscant-health.local",
                "role": UserRole.PATIENT,
                "district": "Manarai Heights",
                "device_identifier": "CHA-BIO-204",
                "is_approved": True,
            },
        )
        if created:
            patient.set_password("PatientPass123!")
            patient.save()
        PatientRecord.objects.get_or_create(
            patient=patient,
            defaults={
                "emergency_contact": "Arel Venn",
                "medical_notes": "Monitoring after Brainworm Rot Type A exposure.",
            },
        )

        doctor, created = User.objects.get_or_create(
            username="doctor_demo",
            defaults={
                "first_name": "Talis",
                "last_name": "Rehn",
                "email": "doctor@coruscant-health.local",
                "role": UserRole.DOCTOR,
                "is_approved": True,
            },
        )
        if created:
            doctor.set_password("DoctorPass123!")
            doctor.save()
        DoctorProfile.objects.get_or_create(
            doctor=doctor,
            defaults={"specialty": "Infectious Disease", "license_id": "DOC-1138"},
        )

        department, created = User.objects.get_or_create(
            username="department_demo",
            defaults={
                "first_name": "Imaging",
                "last_name": "Unit",
                "email": "department@coruscant-health.local",
                "role": UserRole.DEPARTMENT,
                "is_approved": True,
            },
        )
        if created:
            department.set_password("DepartmentPass123!")
            department.save()

        emergency, created = User.objects.get_or_create(
            username="emergency_demo",
            defaults={
                "first_name": "Rapid",
                "last_name": "Response",
                "email": "emergency@coruscant-health.local",
                "role": UserRole.EMERGENCY,
                "is_approved": True,
            },
        )
        if created:
            emergency.set_password("EmergencyPass123!")
            emergency.save()

        HealthReading.objects.get_or_create(
            patient=patient,
            recorded_at=timezone.now(),
            defaults={
                "heart_rate": 76,
                "blood_oxygen": 98,
                "temperature_c": "36.7",
                "systolic_bp": 118,
                "diastolic_bp": 78,
                "symptoms": "Mild fatigue, otherwise stable.",
            },
        )

        DoctorReport.objects.get_or_create(
            patient=patient,
            doctor=doctor,
            report_title="Weekly recovery assessment",
            defaults={
                "trend": "improving",
                "summary": "Vitals are stable and symptom severity continues to decrease.",
                "prescription": "Continue hydration, follow medication plan, and recheck in 72 hours.",
            },
        )

        ServiceOrder.objects.get_or_create(
            patient=patient,
            doctor=doctor,
            department=department,
            service_type="ct_scan",
            defaults={
                "status": ServiceStatus.REQUESTED,
                "notes": "Follow-up scan for neurological observation.",
            },
        )

        SecureDocument.objects.get_or_create(
            owner=patient,
            uploaded_by=doctor,
            title="Initial consultation notes",
            defaults={
                "category": "clinical",
                "original_filename": "consultation-notes.txt",
                "content_type": "text/plain",
                "encrypted_payload": encrypt_bytes(
                    b"Patient admitted with manageable symptoms. Daily device tracking enabled."
                ),
            },
        )

        self.stdout.write(self.style.SUCCESS("Submission demo data is ready."))

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from cryptography.fernet import Fernet

from .models import (
    DoctorProfile,
    DoctorReport,
    HealthReading,
    SecureDocument,
    ServiceOrder,
    User,
    UserRole,
)
from .services import decrypt_bytes


class RegistrationFlowTests(TestCase):
    def test_patient_registration_creates_patient_record_and_requires_approval(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Leia",
                "last_name": "Organa",
                "username": "leia",
                "email": "leia@example.com",
                "role": UserRole.PATIENT,
                "phone_number": "12345",
                "district": "Senate District",
                "device_identifier": "BIO-001",
                "date_of_birth": "1990-01-01",
                "emergency_contact": "Bail Organa",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="leia")
        self.assertFalse(user.is_approved)
        self.assertTrue(hasattr(user, "patient_record"))

    def test_doctor_registration_creates_profile(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Stephen",
                "last_name": "Strange",
                "username": "drstrange",
                "email": "dr@example.com",
                "role": UserRole.DOCTOR,
                "phone_number": "67890",
                "district": "Jedi Quarter",
                "device_identifier": "",
                "specialty": "Neurology",
                "license_id": "DOC-77",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        doctor = User.objects.get(username="drstrange")
        self.assertTrue(DoctorProfile.objects.filter(doctor=doctor, specialty="Neurology").exists())


class ClinicalWorkflowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient1",
            password="ComplexPass123!",
            role=UserRole.PATIENT,
            is_approved=True,
        )
        self.doctor = User.objects.create_user(
            username="doctor1",
            password="ComplexPass123!",
            role=UserRole.DOCTOR,
            is_approved=True,
        )
        self.department = User.objects.create_user(
            username="dept1",
            password="ComplexPass123!",
            role=UserRole.DEPARTMENT,
            is_approved=True,
        )
        self.other_patient = User.objects.create_user(
            username="patient-other",
            password="ComplexPass123!",
            role=UserRole.PATIENT,
            is_approved=True,
        )

    def test_patient_can_submit_reading(self):
        self.client.login(username="patient1", password="ComplexPass123!")
        response = self.client.post(
            reverse("submit_reading"),
            {
                "recorded_at": "2026-04-22T12:30",
                "heart_rate": 72,
                "blood_oxygen": 98,
                "temperature_c": "36.8",
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "symptoms": "Stable",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(HealthReading.objects.filter(patient=self.patient).count(), 1)

    def test_invalid_reading_submission_does_not_create_record(self):
        self.client.login(username="patient1", password="ComplexPass123!")
        response = self.client.post(
            reverse("submit_reading"),
            {
                "recorded_at": "2026-04-22T12:30",
                "heart_rate": 400,
                "blood_oxygen": 98,
                "temperature_c": "36.8",
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "symptoms": "Stable",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is less than or equal to 240.")
        self.assertEqual(HealthReading.objects.filter(patient=self.patient).count(), 0)

    def test_doctor_can_create_report_and_order(self):
        self.client.login(username="doctor1", password="ComplexPass123!")
        report_response = self.client.post(
            reverse("create_report"),
            {
                "patient": self.patient.id,
                "trend": "improving",
                "report_title": "Follow-up",
                "summary": "Patient is improving.",
                "prescription": "Continue current treatment.",
            },
        )
        order_response = self.client.post(
            reverse("create_order"),
            {
                "patient": self.patient.id,
                "department": self.department.id,
                "service_type": "ct_scan",
                "notes": "Brain scan required.",
            },
        )
        self.assertRedirects(report_response, reverse("dashboard"))
        self.assertRedirects(order_response, reverse("dashboard"))
        self.assertEqual(DoctorReport.objects.filter(doctor=self.doctor, patient=self.patient).count(), 1)
        self.assertEqual(ServiceOrder.objects.filter(doctor=self.doctor, patient=self.patient).count(), 1)

    def test_patient_cannot_open_doctor_only_page(self):
        self.client.login(username="patient1", password="ComplexPass123!")
        response = self.client.get(reverse("create_report"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_doctor_only_sees_paginated_patients_list(self):
        for index in range(6):
            User.objects.create_user(
                username=f"patient-extra-{index}",
                password="ComplexPass123!",
                role=UserRole.PATIENT,
                is_approved=True,
            )
        self.client.login(username="doctor1", password="ComplexPass123!")
        response = self.client.get(reverse("dashboard"), {"patients_page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["patients"].number, 2)


class SecureDocumentTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient2",
            password="ComplexPass123!",
            role=UserRole.PATIENT,
            is_approved=True,
        )

    def test_uploaded_documents_are_encrypted_in_database(self):
        self.client.login(username="patient2", password="ComplexPass123!")
        upload = SimpleUploadedFile("report.txt", b"important medical data", content_type="text/plain")
        response = self.client.post(
            reverse("upload_document"),
            {
                "owner": self.patient.id,
                "category": "clinical",
                "title": "Daily report",
                "document": upload,
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        document = SecureDocument.objects.get(title="Daily report")
        self.assertNotEqual(bytes(document.encrypted_payload), b"important medical data")
        self.assertEqual(decrypt_bytes(bytes(document.encrypted_payload)), b"important medical data")

    def test_invalid_encrypted_payload_returns_404(self):
        cipher = Fernet.generate_key()
        upload = SecureDocument.objects.create(
            owner=self.patient,
            uploaded_by=self.patient,
            category="clinical",
            title="Broken file",
            original_filename="broken.txt",
            content_type="text/plain",
            encrypted_payload=Fernet(cipher).encrypt(b"wrong key"),
        )
        self.client.login(username="patient2", password="ComplexPass123!")
        response = self.client.get(reverse("download_document", args=[upload.id]))
        self.assertEqual(response.status_code, 404)

    def test_other_patient_cannot_download_document(self):
        other_patient = User.objects.create_user(
            username="patient3",
            password="ComplexPass123!",
            role=UserRole.PATIENT,
            is_approved=True,
        )
        document = SecureDocument.objects.create(
            owner=self.patient,
            uploaded_by=self.patient,
            category="clinical",
            title="Private file",
            original_filename="private.txt",
            content_type="text/plain",
            encrypted_payload=b"gAAAAABpplaceholder",
        )
        self.client.login(username="patient3", password="ComplexPass123!")
        response = self.client.get(reverse("download_document", args=[document.id]))
        self.assertEqual(response.status_code, 404)


class DeploymentReadinessTests(TestCase):
    def test_healthcheck_endpoint_returns_ok(self):
        response = self.client.get(reverse("healthcheck"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_seed_demo_command_creates_submission_accounts(self):
        call_command("seed_demo")
        self.assertTrue(User.objects.filter(username="cha_admin", role=UserRole.ADMINISTRATOR).exists())
        self.assertTrue(User.objects.filter(username="patient_demo", role=UserRole.PATIENT).exists())
        self.assertTrue(User.objects.filter(username="doctor_demo", role=UserRole.DOCTOR).exists())


class ApprovalQueueTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1",
            password="ComplexPass123!",
            role=UserRole.ADMINISTRATOR,
        )
        self.patient = User.objects.create_user(
            username="pending1",
            password="ComplexPass123!",
            role=UserRole.PATIENT,
            is_approved=False,
        )

    def test_non_admin_cannot_access_approval_queue(self):
        self.client.login(username="pending1", password="ComplexPass123!")
        response = self.client.get(reverse("approval_queue"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_approval_queue_is_paginated(self):
        for index in range(6):
            User.objects.create_user(
                username=f"pending-extra-{index}",
                password="ComplexPass123!",
                role=UserRole.PATIENT,
                is_approved=False,
            )
        self.client.login(username="admin1", password="ComplexPass123!")
        response = self.client.get(reverse("approval_queue"), {"page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pending_users"].number, 2)

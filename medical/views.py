from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import (
    ApprovalForm,
    DoctorReportForm,
    EmergencyIntakeForm,
    HealthReadingForm,
    OrderResultForm,
    RegistrationForm,
    SecureDocumentForm,
    ServiceOrderForm,
    StyledAuthenticationForm,
)
from .models import (
    DoctorReport,
    EmergencyIntake,
    HealthReading,
    SecureDocument,
    ServiceOrder,
    ServiceStatus,
    User,
    UserRole,
)
from .services import decrypt_bytes


class CHAloginView(LoginView):
    authentication_form = StyledAuthenticationForm
    template_name = "medical/login.html"


def landing(request):
    context = {
        "patient_count": User.objects.filter(role=UserRole.PATIENT).count(),
        "doctor_count": User.objects.filter(role=UserRole.DOCTOR).count(),
        "reading_count": HealthReading.objects.count(),
        "report_count": DoctorReport.objects.count(),
    }
    return render(request, "medical/landing.html", context)


def healthcheck(request):
    return JsonResponse({"status": "ok"})


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Registration completed. Administrator approval is required before clinical access is enabled."
                if not user.is_approved
                else "Registration completed successfully.",
            )
            return redirect("dashboard")
    else:
        form = RegistrationForm()
    return render(request, "medical/register.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    context = {
        "pending_approvals": User.objects.filter(is_approved=False).exclude(role=UserRole.ADMINISTRATOR)[:5],
        "latest_readings": HealthReading.objects.all()[:6],
        "latest_reports": DoctorReport.objects.select_related("patient", "doctor")[:6],
        "latest_orders": ServiceOrder.objects.select_related("patient", "doctor", "department")[:6],
        "latest_intakes": EmergencyIntake.objects.all()[:6],
    }

    if user.role == UserRole.PATIENT:
        context.update(
            {
                "my_readings": user.health_readings.all()[:8],
                "my_reports": user.doctor_reports.select_related("doctor")[:8],
                "my_documents": user.documents.all()[:8],
            }
        )
    elif user.role == UserRole.DOCTOR:
        context.update(
            {
                "patients": User.objects.filter(role=UserRole.PATIENT, is_approved=True),
                "doctor_reports": user.written_reports.select_related("patient")[:8],
                "doctor_orders": user.issued_service_orders.select_related("patient", "department")[:8],
            }
        )
    elif user.role == UserRole.DEPARTMENT:
        context.update(
            {
                "assigned_orders": ServiceOrder.objects.filter(department=user)[:8],
            }
        )
    elif user.role == UserRole.ADMINISTRATOR:
        context.update(
            {
                "approval_total": User.objects.filter(is_approved=False).exclude(role=UserRole.ADMINISTRATOR).count(),
            }
        )
    elif user.role == UserRole.EMERGENCY:
        context.update({"recent_intakes": user.emergency_intakes.all()[:8]})

    return render(request, "medical/dashboard.html", context)


@login_required
@role_required(UserRole.PATIENT)
def submit_reading(request):
    if not request.user.is_approved:
        messages.error(request, "Your account must be approved before health data can be submitted.")
        return redirect("dashboard")
    if request.method == "POST":
        form = HealthReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.patient = request.user
            reading.save()
            messages.success(request, "Health reading uploaded successfully.")
            return redirect("dashboard")
    else:
        form = HealthReadingForm()
    return render(request, "medical/form_page.html", {"form": form, "title": "Upload health reading"})


@login_required
@role_required(UserRole.DOCTOR)
def create_report(request):
    if not request.user.is_approved:
        messages.error(request, "Administrator approval is still pending for your account.")
        return redirect("dashboard")
    if request.method == "POST":
        form = DoctorReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.doctor = request.user
            report.save()
            messages.success(request, "Clinical report saved for the patient.")
            return redirect("dashboard")
    else:
        form = DoctorReportForm()
    return render(request, "medical/form_page.html", {"form": form, "title": "Write doctor report"})


@login_required
@role_required(UserRole.DOCTOR)
def create_order(request):
    if request.method == "POST":
        form = ServiceOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.doctor = request.user
            if order.status == ServiceStatus.COMPLETED and not order.completed_at:
                order.completed_at = timezone.now()
            order.save()
            messages.success(request, "Service order submitted to the department queue.")
            return redirect("dashboard")
    else:
        form = ServiceOrderForm()
    return render(request, "medical/form_page.html", {"form": form, "title": "Create service order"})


@login_required
@role_required(UserRole.DEPARTMENT)
def upload_order_result(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id)
    if order.department and order.department != request.user:
        raise Http404("Order not assigned to this department.")
    if request.method == "POST":
        form = OrderResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.order = order
            result.uploaded_by = request.user
            result.save()
            order.status = ServiceStatus.COMPLETED
            order.department = request.user
            order.completed_at = timezone.now()
            order.save(update_fields=["status", "department", "completed_at"])
            messages.success(request, "Order result uploaded successfully.")
            return redirect("dashboard")
    else:
        form = OrderResultForm()
    return render(
        request,
        "medical/form_page.html",
        {"form": form, "title": f"Upload result for order #{order.id}"},
    )


@login_required
@role_required(UserRole.ADMINISTRATOR)
def approval_queue(request):
    pending_users = User.objects.filter(is_approved=False).exclude(role=UserRole.ADMINISTRATOR)
    if request.method == "POST":
        user = get_object_or_404(pending_users, pk=request.POST.get("user_id"))
        form = ApprovalForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{user.full_display_name} approval updated.")
            return redirect("approval_queue")
    return render(request, "medical/approval_queue.html", {"pending_users": pending_users})


@login_required
@role_required(UserRole.EMERGENCY, UserRole.ADMINISTRATOR)
def emergency_intake(request):
    if request.method == "POST":
        form = EmergencyIntakeForm(request.POST)
        if form.is_valid():
            intake = form.save(commit=False)
            intake.created_by = request.user
            intake.save()
            messages.success(request, "Emergency intake saved.")
            return redirect("dashboard")
    else:
        form = EmergencyIntakeForm()
    return render(request, "medical/form_page.html", {"form": form, "title": "Fast emergency intake"})


@login_required
def upload_document(request):
    owner_queryset = User.objects.filter(pk=request.user.pk)
    if request.user.role in {UserRole.DOCTOR, UserRole.ADMINISTRATOR, UserRole.DEPARTMENT}:
        owner_queryset = User.objects.filter(role=UserRole.PATIENT, is_approved=True)
    if request.method == "POST":
        form = SecureDocumentForm(request.POST, request.FILES, owner_queryset=owner_queryset)
        if form.is_valid():
            form.save(uploaded_by=request.user)
            messages.success(request, "Encrypted document uploaded successfully.")
            return redirect("dashboard")
    else:
        form = SecureDocumentForm(owner_queryset=owner_queryset, initial={"owner": request.user})
    return render(request, "medical/form_page.html", {"form": form, "title": "Upload encrypted document"})


@login_required
def download_document(request, document_id):
    document = get_object_or_404(SecureDocument, pk=document_id)
    if request.user != document.owner and request.user not in {document.uploaded_by}:
        if request.user.role not in {UserRole.ADMINISTRATOR, UserRole.DOCTOR, UserRole.DEPARTMENT}:
            raise Http404("Document unavailable.")
    payload = decrypt_bytes(bytes(document.encrypted_payload))
    response = HttpResponse(payload, content_type=document.content_type or "application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{document.original_filename}"'
    return response

# Create your views here.

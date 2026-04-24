from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

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
)


@admin.register(User)
class CHAUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "CHA profile",
            {
                "fields": ("role", "is_approved", "phone_number", "district", "device_identifier"),
            },
        ),
    )
    list_display = ("username", "email", "role", "is_approved", "is_staff")
    list_filter = ("role", "is_approved", "is_staff")


admin.site.register(PatientRecord)
admin.site.register(DoctorProfile)
admin.site.register(HealthReading)
admin.site.register(DoctorReport)
admin.site.register(ServiceOrder)
admin.site.register(OrderResult)
admin.site.register(SecureDocument)
admin.site.register(EmergencyIntake)

# Register your models here.

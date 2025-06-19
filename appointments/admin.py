from django.contrib import admin
from .models import Appointment, AppointmentStatusHistory

class AppointmentStatusHistoryInline(admin.TabularInline):
    model = AppointmentStatusHistory
    extra = 0
    readonly_fields = ('previous_status', 'new_status', 'changed_by', 'reason', 'changed_at')
    can_delete = False

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'doctor_name', 'appointment_datetime', 'status', 'appointment_type', 'is_urgent')
    list_filter = ('status', 'appointment_type', 'is_urgent', 'appointment_datetime', 'doctor')
    search_fields = ('patient__user__email', 'doctor__user__email', 'patient__user__first_name', 'reason')
    raw_id_fields = ('patient', 'doctor')
    inlines = [AppointmentStatusHistoryInline]
    readonly_fields = ('created_at', 'updated_at')

    def patient_name(self, obj):
        return obj.patient.full_name
    def doctor_name(self, obj):
        return obj.doctor.full_name
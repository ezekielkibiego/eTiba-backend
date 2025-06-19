from django.contrib import admin
from .models import MedicalRecord, MedicalRecordAttachment, MedicalRecordAccess

class MedicalRecordAttachmentInline(admin.TabularInline):
    model = MedicalRecordAttachment
    extra = 1
    readonly_fields = ('filename', 'file_size', 'content_type', 'uploaded_at')
    fields = ('file', 'filename', 'file_size', 'content_type', 'uploaded_by', 'uploaded_at')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient_name', 'doctor_name', 'record_type', 'appointment_summary', 'created_at', 'is_deleted')
    list_filter = ('record_type', 'is_confidential', 'created_at', 'is_deleted', 'doctor', 'patient')
    search_fields = ('title', 'summary', 'patient__user__email', 'patient__user__first_name', 'patient__user__last_name', 'doctor__user__email')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')
    raw_id_fields = ('patient', 'doctor', 'appointment', 'created_by', 'updated_by')
    inlines = [MedicalRecordAttachmentInline]
    fieldsets = (
        (None, {'fields': ('patient', 'doctor', 'appointment', 'record_type', 'title', 'summary')}),
        ('Details', {'fields': ('diagnosis', 'treatment_plan', 'medications', 'allergies', 'lab_results', 'vital_signs')}),
        ('Status', {'fields': ('is_confidential', 'is_deleted', 'deleted_at')}),
        ('Audit', {'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'), 'classes': ('collapse',)}),
    )

    def patient_name(self, obj):
        return obj.patient.user.get_full_name() if obj.patient and obj.patient.user else '-'
    patient_name.short_description = 'Patient'

    def doctor_name(self, obj):
        return obj.doctor.user.get_full_name() if obj.doctor and obj.doctor.user else '-'
    doctor_name.short_description = 'Doctor'

    def appointment_summary(self, obj):
        return f"Appt ID: {obj.appointment.id}" if obj.appointment else '-'
    appointment_summary.short_description = 'Appointment'

@admin.register(MedicalRecordAccess)
class MedicalRecordAccessAdmin(admin.ModelAdmin):
    list_display = ('medical_record_title', 'accessed_by_user', 'access_type', 'created_at', 'ip_address')
    list_filter = ('access_type', 'created_at')
    search_fields = ('medical_record__title', 'accessed_by__email', 'ip_address')
    readonly_fields = ('created_at',)

    def medical_record_title(self, obj):
        return obj.medical_record.title
    medical_record_title.short_description = 'Record Title'

    def accessed_by_user(self, obj):
        return obj.accessed_by.email
    accessed_by_user.short_description = 'Accessed By'
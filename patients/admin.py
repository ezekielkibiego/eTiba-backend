from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('get_user_full_name', 'date_of_birth', 'gender', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_filter = ('gender', 'created_at', 'updated_at')
    raw_id_fields = ('user',) 
    readonly_fields = ('created_at', 'updated_at', 'get_age')

    fieldsets = (
        (None, {
            'fields': ('user', 'date_of_birth', 'gender', 'get_age')
        }),
        ('Contact Information', {
            'fields': ('address', 'emergency_contact')
        }),
        ('Insurance Details', {
            'fields': ('insurance_provider', 'insurance_number')
        }),
        ('Medical Information', {
            'fields': ('medical_history', 'allergies', 'current_medications')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_user_full_name(self, obj):
        return obj.user.get_full_name()
    get_user_full_name.short_description = 'Patient Name'

    def get_age(self, obj):
        return obj.age
    get_age.short_description = 'Age'

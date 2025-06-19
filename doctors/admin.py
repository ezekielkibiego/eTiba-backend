from django.contrib import admin
from .models import Doctor, Specialization, DoctorSpecialization, DoctorAvailability, DoctorUnavailability

class DoctorSpecializationInline(admin.TabularInline):
    model = DoctorSpecialization
    extra = 1
    autocomplete_fields = ['specialization']

class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 1
    fields = ('day_of_week', 'start_time', 'end_time', 'break_start', 'break_end', 'is_active')
    ordering = ('day_of_week', 'start_time')

class DoctorUnavailabilityInline(admin.TabularInline):
    model = DoctorUnavailability
    extra = 1
    fields = ('start_date', 'end_date', 'reason')

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'license_number', 'primary_specialization_display', 'years_of_experience', 'consultation_fee', 'is_user_active', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'license_number')
    list_filter = ('is_available', 'specializations', 'created_at')
    raw_id_fields = ('user',) # For easier user selection
    inlines = [DoctorSpecializationInline, DoctorAvailabilityInline, DoctorUnavailabilityInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('user', 'license_number', 'years_of_experience', 'consultation_fee')
        }),
        ('Profile Details', {
            'fields': ('bio', 'office_address', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.full_name
    get_full_name.short_description = 'Doctor Name'

    def primary_specialization_display(self, obj):
        primary_spec = obj.primary_specialization
        return primary_spec.name if primary_spec else '-'
    primary_specialization_display.short_description = 'Primary Specialization'

    def is_user_active(self, obj):
        return obj.user.is_active
    is_user_active.boolean = True
    is_user_active.short_description = 'User Active'

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'get_day_of_week_display', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active', 'doctor')
    search_fields = ('doctor__user__email', 'doctor__user__first_name', 'doctor__user__last_name')
    autocomplete_fields = ['doctor']

@admin.register(DoctorUnavailability)
class DoctorUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'reason', 'created_at')
    list_filter = ('doctor', 'start_date', 'end_date')
    search_fields = ('doctor__user__email', 'doctor__user__first_name', 'doctor__user__last_name', 'reason')
    autocomplete_fields = ['doctor']

# DoctorSpecialization is managed via inline in DoctorAdmin,
# but can be registered separately if direct management is needed.
# admin.site.register(DoctorSpecialization)
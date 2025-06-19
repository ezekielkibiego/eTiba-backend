import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Appointment(models.Model):
    """
    Appointment model linking patients and doctors
    Core model for the appointment scheduling system
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow Up'),
        ('emergency', 'Emergency'),
        ('routine_checkup', 'Routine Checkup'),
        ('procedure', 'Procedure'),
        ('test_results', 'Test Results Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'patients.Patient', 
        on_delete=models.CASCADE, 
        related_name='appointments'
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', 
        on_delete=models.CASCADE, 
        related_name='appointments'
    )
    appointment_datetime = models.DateTimeField()
    duration = models.PositiveIntegerField(
        default=30, 
        validators=[MinValueValidator(15), MaxValueValidator(240)],
        help_text="Duration in minutes"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='consultation')
    reason = models.TextField(help_text="Reason for the appointment")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes from patient")
    doctor_notes = models.TextField(blank=True, null=True, help_text="Doctor's notes after appointment")
    symptoms = models.TextField(blank=True, null=True, help_text="Patient's reported symptoms")
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        # Prevent double booking - same doctor can't have appointments at same time
        unique_together = ['doctor', 'appointment_datetime']
        indexes = [
            models.Index(fields=['patient', 'appointment_datetime']),
            models.Index(fields=['doctor', 'appointment_datetime']),
            models.Index(fields=['status']),
            models.Index(fields=['appointment_datetime']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['appointment_datetime']
    
    def __str__(self):
        return f"{self.patient.full_name} with {self.doctor.full_name} on {self.appointment_datetime}"
    
    @property
    def appointment_end_time(self):
        """Calculate appointment end time"""
        from datetime import timedelta
        return self.appointment_datetime + timedelta(minutes=self.duration)
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        return self.appointment_datetime < timezone.now()
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_datetime.date() == timezone.now().date()
    
    @property
    def can_be_cancelled(self):
        """Check if appointment can be cancelled (not in the past and not completed)"""
        return not self.is_past and self.status not in ['completed', 'cancelled', 'no_show']
    
    def clean(self):
        """Validate appointment constraints"""
        from django.core.exceptions import ValidationError

        if self._state.adding: # True if the instance is being created (new)
            if self.appointment_datetime <= timezone.now():
                raise ValidationError({"appointment_datetime": "New appointment must be scheduled for a future date and time."})
        else: # Instance is being updated (existing)
            # If appointment_datetime is being changed for an existing appointment
            dirty_fields = self.get_dirty_fields() # This is now safe to call
            if 'appointment_datetime' in dirty_fields: # Check if the datetime field was actually changed
                if self.appointment_datetime <= timezone.now():
                    raise ValidationError({"appointment_datetime": "Rescheduled appointment must be for a future date and time."})
   
        # Check if appointment is during doctor's available hours
        # This would be implemented with business logic in services

    def get_dirty_fields(self):
        """
        Helper method to check which fields have changed on an existing model instance
        before it's saved. It compares current values to the ones in the database.
        Returns an empty dict if the instance is new or not yet saved with a PK.
        """
        if self._state.adding or not self.pk:
            return {}
        model_class = self.__class__
        original = model_class._default_manager.get(pk=self.pk) # Get the original state from DB
        dirty_fields = {}
        for field in model_class._meta.fields:
            # Compare the current value of the field with the original value
            if getattr(self, field.attname) != getattr(original, field.attname):
                dirty_fields[field.name] = getattr(self, field.attname)
        return dirty_fields

        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AppointmentStatusHistory(models.Model):
    """
    Track appointment status changes for audit purposes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='status_history')
    # Allow previous_status to be null for the very first status entry of an appointment.
    previous_status = models.CharField(max_length=20, choices=Appointment.STATUS_CHOICES, null=True, blank=True) 
    new_status = models.CharField(max_length=20, choices=Appointment.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'appointment_status_history'
        ordering = ['-changed_at']
    
    def __str__(self):
        # Improved string representation: show "Initial" if no previous status, and show who changed it.
        return f"Appointment {self.appointment.id}: {self.previous_status or 'Initial'} → {self.new_status} by {self.changed_by or 'System'}"

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.conf import settings
User = get_user_model()


class Specialization(models.Model):
    """
    Medical specializations for doctors
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'specializations'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Doctor(models.Model):
    """
    Doctor model storing doctor-specific information
    One-to-one relationship with User model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    license_number = models.CharField(max_length=50, unique=True)
    specializations = models.ManyToManyField(Specialization, through='DoctorSpecialization')
    years_of_experience = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    bio = models.TextField(blank=True, null=True, help_text="Doctor's biography and qualifications")
    office_address = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True, help_text="Whether doctor is accepting new appointments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctors'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['license_number']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"
    
    @property
    def full_name(self):
        return f"Dr. {self.user.get_full_name()}"
    
    @property
    def primary_specialization(self):
        """Get the first specialization"""
        return self.specializations.first()


class DoctorSpecialization(models.Model):
    """
    Through model for Doctor-Specialization many-to-many relationship
    Allows for additional fields like certification date, board certification, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    board_certified = models.BooleanField(default=False)
    certification_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_specializations'
        unique_together = ['doctor', 'specialization']
    
    def __str__(self):
        return f"{self.doctor} - {self.specialization}"


class DoctorAvailability(models.Model):
    """
    Doctor's weekly availability schedule
    Defines when a doctor is available for appointments
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability_schedule')
    day_of_week = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_start = models.TimeField(blank=True, null=True, help_text="Lunch break start time")
    break_end = models.TimeField(blank=True, null=True, help_text="Lunch break end time")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_availability'
        unique_together = ['doctor', 'day_of_week']
        indexes = [
            models.Index(fields=['doctor', 'day_of_week']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()}: {self.start_time}-{self.end_time}"
    
    def clean(self):
        """Validate that end_time is after start_time"""
        from django.core.exceptions import ValidationError
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        
        if self.break_start and self.break_end:
            if self.break_start >= self.break_end:
                raise ValidationError("Break end time must be after break start time")
            if not (self.start_time <= self.break_start < self.break_end <= self.end_time):
                raise ValidationError("Break times must be within working hours")


class DoctorUnavailability(models.Model):
    """
    Doctor's unavailable dates (vacations, conferences, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='unavailable_dates')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_unavailability'
        indexes = [
            models.Index(fields=['doctor', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.doctor} unavailable: {self.start_date} to {self.end_date}"
    
    def clean(self):
        """Validate that end_date is after start_date"""
        from django.core.exceptions import ValidationError
        if self.start_date > self.end_date:
            raise ValidationError("End date must be after start date")

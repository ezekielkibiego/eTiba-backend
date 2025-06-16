import uuid
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings

class Patient(models.Model):
    """
    Patient model storing patient-specific information
    One-to-one relationship with User model
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to Say')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number format: '+999999999'")]
    )
    insurance_provider = models.CharField(max_length=100, blank=True, null=True)
    insurance_number = models.CharField(max_length=50, blank=True, null=True)
    medical_history = models.TextField(blank=True, null=True, help_text="Brief medical history")
    allergies = models.TextField(blank=True, null=True, help_text="Known allergies")
    current_medications = models.TextField(blank=True, null=True, help_text="Current medications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patients'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['date_of_birth']),
            models.Index(fields=['insurance_provider']),
        ]
    
    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"
    
    @property
    def age(self):
        """Calculate patient's age"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def full_name(self):
        return self.user.get_full_name()


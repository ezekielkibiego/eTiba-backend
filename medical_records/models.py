import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.conf import settings

User = get_user_model()

# apps/common/models.py (Base models and utilities) - Assuming these are defined elsewhere or here for context

class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # Added for completeness if not abstractly inherited
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class AuditModel(TimeStampedModel): # Assuming TimeStampedModel is defined
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )

    class Meta:
        abstract = True

class MedicalRecord(AuditModel, SoftDeleteModel): # Inherit from TimeStampedModel and SoftDeleteModel
    """
    Medical records for patients
    Linked to appointments and accessible with proper permissions
    """
    RECORD_TYPE_CHOICES = [
        ('consultation', 'Consultation Notes'),
        ('diagnosis', 'Diagnosis'),
        ('prescription', 'Prescription'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging Result'),
        ('procedure', 'Procedure Notes'),
        ('discharge', 'Discharge Summary'),
        ('referral', 'Referral'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'patients.Patient', 
        on_delete=models.CASCADE, 
        related_name='medical_records'
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', 
        on_delete=models.SET_NULL, # Changed from CASCADE to SET_NULL
        null=True,                 # Allow doctor to be null if they are deleted
        related_name='created_medical_records' # Slightly more specific related_name
    )
    appointment = models.ForeignKey(
        'appointments.Appointment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='medical_records'
    )
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True, null=True, help_text="Brief summary of the record")
    diagnosis = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True, help_text="Proposed treatment plan")
    medications = models.JSONField(blank=True, null=True, help_text="List of prescribed medications and dosages")
    allergies = models.JSONField(blank=True, null=True, help_text="Known allergies and reactions")
    lab_results = models.JSONField(blank=True, null=True, help_text="Structured lab results data")
    vital_signs = models.JSONField(blank=True, null=True, help_text="Blood pressure, temperature, etc.")
    is_confidential = models.BooleanField(default=False, help_text="Highly sensitive information")
    # created_at and updated_at are inherited from TimeStampedModel
    # is_deleted and deleted_at are inherited from SoftDeleteModel
    
    class Meta:
        db_table = 'medical_records'
        indexes = [
            models.Index(fields=['patient', 'created_at']),
            models.Index(fields=['doctor', 'created_at']),
            models.Index(fields=['record_type']),
            models.Index(fields=['appointment']),
        ]
        ordering = ['-updated_at', '-created_at'] # Order by most recently updated/created
    
    def __str__(self):
        return f"Medical Record: {self.title} - {self.patient.full_name}"


class MedicalRecordAttachment(TimeStampedModel): # Inherit from TimeStampedModel
    """
    File attachments for medical records (lab reports, images, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        MedicalRecord, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='medical_records/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])]
    )
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    content_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='uploaded_attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_record_attachments'
    
    def __str__(self):
        return f"Attachment: {self.filename}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class MedicalRecordAccess(TimeStampedModel): # Inherit from TimeStampedModel
    """
    Audit trail for medical record access (HIPAA compliance)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        MedicalRecord, 
        on_delete=models.CASCADE, 
        related_name='access_logs'
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='medical_record_accesses'
    )
    access_type = models.CharField(
        max_length=20, 
        choices=[
            ('view', 'View'),
            ('edit', 'Edit'),
            ('delete', 'Delete'),
            ('download', 'Download'),
        ]
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    # accessed_at will be created_at from TimeStampedModel
    
    class Meta:
        db_table = 'medical_record_access'
        indexes = [
            models.Index(fields=['medical_record', 'created_at']), # Use 'created_at'
            models.Index(fields=['accessed_by', 'created_at']),   # Use 'created_at'
        ]
    
    def __str__(self):
        return f"{self.accessed_by.get_full_name() if self.accessed_by else 'Unknown User'} {self.get_access_type_display()} record: {self.medical_record.title} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
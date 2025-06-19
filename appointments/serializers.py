from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
import logging

from .models import Appointment, AppointmentStatusHistory
from patients.models import Patient
from doctors.models import Doctor
from patients.serializers import PatientUserSerializer # For displaying patient user details
from doctors.serializers import DoctorUserSerializer # For displaying doctor user details
from .services import AppointmentService # We'll define this later for complex logic
from notifications.tasks import (
    create_appointment_creation_notification_task,
    create_appointment_change_notification_task
)

logger = logging.getLogger(__name__)

class AppointmentPatientSerializer(serializers.ModelSerializer):
    """Simplified Patient serializer for appointments."""
    user = PatientUserSerializer(read_only=True)
    class Meta:
        model = Patient
        fields = ['id', 'user', 'full_name']

class AppointmentDoctorSerializer(serializers.ModelSerializer):
    """Simplified Doctor serializer for appointments."""
    user = DoctorUserSerializer(read_only=True)
    class Meta:
        model = Doctor
        fields = ['id', 'user', 'full_name']

class AppointmentStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True, allow_null=True)
    class Meta:
        model = AppointmentStatusHistory
        fields = ['id', 'previous_status', 'new_status', 'reason', 'changed_by_email', 'changed_at']

class AppointmentSerializer(serializers.ModelSerializer):
    patient = AppointmentPatientSerializer(read_only=True)
    doctor = AppointmentDoctorSerializer(read_only=True)
    patient_id = serializers.UUIDField(write_only=True, required=False) # Required for admin/doctor creating for others
    doctor_id = serializers.UUIDField(write_only=True)
    status_history = AppointmentStatusHistorySerializer(many=True, read_only=True)
    appointment_end_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'patient_id', 'doctor_id', 'appointment_datetime', 
            'duration', 'status', 'appointment_type', 'reason', 'notes', 
            'doctor_notes', 'symptoms', 'is_urgent', 'appointment_end_time',
            'status_history', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status_history', 'created_at', 'updated_at', 'appointment_end_time']

    def validate_appointment_datetime(self, value):
        if value <= timezone.now():
            # For new appointments or if datetime is changed for existing ones
            if not self.instance or (self.instance and self.instance.appointment_datetime != value):
                 raise serializers.ValidationError("Appointment must be scheduled for a future date and time.")
        return value

    def validate(self, attrs):
        doctor_id = attrs.get('doctor_id')
        appointment_datetime = attrs.get('appointment_datetime')
        duration = attrs.get('duration', self.instance.duration if self.instance else Appointment._meta.get_field('duration').default)

        # Basic validation for doctor existence
        try:
            doctor = Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            raise serializers.ValidationError({"doctor_id": "Doctor not found."})
        
        attrs['doctor'] = doctor # Add doctor instance to attrs for create/update

        # Patient validation
        request = self.context.get('request')
        patient_id = attrs.get('patient_id')

        if request and request.user.role == 'PATIENT':
            try:
                patient = Patient.objects.get(user=request.user)
                attrs['patient'] = patient
                if patient_id and patient_id != patient.id: # Patient trying to book for someone else
                    raise serializers.ValidationError({"patient_id": "You can only book appointments for yourself."})
            except Patient.DoesNotExist:
                raise serializers.ValidationError("Patient profile not found for the current user.")
        elif patient_id: # Admin/Doctor creating for a specific patient
            try:
                attrs['patient'] = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                raise serializers.ValidationError({"patient_id": "Patient not found."})
        elif not self.instance : # patient_id is required if not a patient user and creating new
             raise serializers.ValidationError({"patient_id": "Patient ID is required."})


        # Placeholder for advanced availability and conflict checks
        # This should ideally use AppointmentService
        if appointment_datetime: # Only check if datetime is being set/changed
            if not AppointmentService.is_doctor_available(doctor, appointment_datetime, duration, appointment_id=self.instance.id if self.instance else None):
                raise serializers.ValidationError("Doctor is not available at the selected time or there's a conflict.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('patient_id', None) # Already handled and set as 'patient' instance
        validated_data.pop('doctor_id', None)   # Already handled and set as 'doctor' instance
        
        appointment = Appointment.objects.create(**validated_data)
        # Create initial status history
        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            new_status=appointment.status,
            changed_by=self.context['request'].user if self.context.get('request') else None
        )
        
        # Trigger notification task for appointment creation
        if self.context.get('request') and self.context['request'].user:
            actor_user_id = str(self.context['request'].user.id)
            transaction.on_commit(
                lambda: create_appointment_creation_notification_task.delay(
                    str(appointment.id), actor_user_id
                )
            )
        return appointment

    @transaction.atomic
    def update(self, instance, validated_data):
        print("AppointmentSerializer.update() called")  # Add this line
        logger.warning("AppointmentSerializer.update() called")  # And this for logs
        original_status = instance.status
        original_datetime = instance.appointment_datetime

        actor_user = self.context['request'].user if self.context.get('request') else None
        actor_user_id_str = str(actor_user.id) if actor_user else None

        validated_data.pop('patient_id', None)
        validated_data.pop('doctor_id', None)

        # Update the instance
        updated_instance = super().update(instance, validated_data)

        status_changed = updated_instance.status != original_status
        datetime_changed = updated_instance.appointment_datetime != original_datetime

        if status_changed:
            status_change_reason = validated_data.get('status_change_reason', "Appointment details updated.")
            AppointmentStatusHistory.objects.create(
                appointment=updated_instance,
                previous_status=original_status,
                new_status=updated_instance.status,
                changed_by=actor_user,
                reason=status_change_reason
            )

        # After updating, trigger notification if significant fields changed
        if actor_user_id_str and (status_changed or datetime_changed):
            transaction.on_commit(
                lambda: create_appointment_change_notification_task.delay(
                    appointment_id=str(instance.id),
                    actor_user_id=actor_user_id_str,
                    patient_verb="Appointment Updated",
                    doctor_verb="Appointment Updated",
                    patient_description="Your appointment has been updated.",
                    doctor_description="An appointment has been updated."
                )
            )
        return instance

class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    class Meta:
        model = Appointment
        fields = ['status', 'reason'] # 'reason' is for the status history

class AvailabilityCheckSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=True)
    date = serializers.DateField(required=True)
    duration = serializers.IntegerField(required=False, default=30, min_value=15) # Default duration 30 mins

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Cannot check availability for past dates.")
        return value
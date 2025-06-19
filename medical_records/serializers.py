from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import MedicalRecord, MedicalRecordAttachment
from patients.serializers import PatientUserSerializer # For displaying patient user info
from doctors.serializers import DoctorUserSerializer # For displaying doctor user info
from appointments.serializers import AppointmentSerializer # For displaying appointment info (optional)
from auth_user.models import User as AuthUserModel 

User = get_user_model()

class MedicalRecordAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True, allow_null=True)

    class Meta:
        model = MedicalRecordAttachment
        fields = [
            'id', 'medical_record', 'file', 'filename', 'file_size', 
            'content_type', 'uploaded_by', 'uploaded_by_email', 'uploaded_at'
        ]
        read_only_fields = ['id', 'filename', 'file_size', 'content_type', 'uploaded_at', 'uploaded_by_email']
        extra_kwargs = {
            'medical_record': {'write_only': True, 'required': False}, # Usually set via URL or parent serializer
            'uploaded_by': {'write_only': True, 'required': False}, # Will be set to request.user
            'file': {'write_only': True, 'required': True}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user
        
        # Extract file specific info if not already handled by model's save
        uploaded_file = validated_data.get('file')
        if uploaded_file:
            validated_data['filename'] = uploaded_file.name
            validated_data['file_size'] = uploaded_file.size
            validated_data['content_type'] = uploaded_file.content_type

        return super().create(validated_data)

class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_details = PatientUserSerializer(source='patient.user', read_only=True)
    doctor_details = DoctorUserSerializer(source='doctor.user', read_only=True)
    # appointment_details = AppointmentSerializer(source='appointment', read_only=True, allow_null=True) # Optional
    attachments = MedicalRecordAttachmentSerializer(many=True, read_only=True, source='record_attachments')
    
    # created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    # updated_by_email = serializers.EmailField(source='updated_by.email', read_only=True, allow_null=True)

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'patient_details', 'doctor', 'doctor_details', 
            'appointment', #'appointment_details', 
            'record_type', 'title', 'summary', 
            'diagnosis', 'treatment_plan', 'medications', 'allergies', 
            'lab_results', 'vital_signs', 'is_confidential', 
            'attachments',
            'created_at', 'updated_at', 'created_by', 'updated_by',
            # 'created_by_email', 'updated_by_email'
        ]
        read_only_fields = [
            'id', 'patient_details', 'doctor_details', #'appointment_details', 
            'attachments', 'created_at', 'updated_at', 
            'created_by', 'updated_by', 
            # 'created_by_email', 'updated_by_email'
        ]
        extra_kwargs = {
            'patient': {'write_only': True, 'required': True},
            'doctor': {'write_only': True, 'required': False}, # Will be set to request.user.doctor_profile
            'appointment': {'required': False, 'allow_null': True},
            'created_by': {'read_only': True}, # Should be set automatically
            'updated_by': {'read_only': True}, # Should be set automatically
        }

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # Set doctor from the logged-in user if they are a doctor
        if user.is_authenticated and user.role == AuthUserModel.Role.DOCTOR and hasattr(user, 'doctor_profile'):
            validated_data['doctor'] = user.doctor_profile
        elif 'doctor' not in validated_data: # If not set by user and user is not a doctor, raise error or handle
            raise serializers.ValidationError("Doctor must be specified or the creator must be a doctor.")

        # Set created_by and updated_by
        if user.is_authenticated:
            validated_data['created_by'] = user
            validated_data['updated_by'] = user
            
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user

        # Set updated_by
        if user.is_authenticated:
            validated_data['updated_by'] = user

        # Prevent changing the patient or doctor after creation through this serializer
        validated_data.pop('patient', None)
        validated_data.pop('doctor', None)
            
        return super().update(instance, validated_data)
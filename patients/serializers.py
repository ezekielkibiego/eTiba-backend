from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from django.urls import reverse # For email link
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

from .models import Patient
from auth_user.models import User as AuthUserModel 
from auth_user.utils import account_activation_token 

User = get_user_model()

class PatientUserSerializer(serializers.ModelSerializer):
    """Serializer for User fields relevant to Patient profile display/update."""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_active']
        read_only_fields = ['id', 'email', 'is_active'] 

class PatientProfileSerializer(serializers.ModelSerializer):
    """Serializer for the Patient model, including nested User details for GET and PUT."""
    user = PatientUserSerializer()

    class Meta:
        model = Patient
        fields = [
            'id', 'user', 'date_of_birth', 'gender', 'address',
            'emergency_contact', 'insurance_provider', 'insurance_number',
            'medical_history', 'allergies', 'current_medications',
            'age', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'age', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        # Update Patient fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update nested User fields if present
        if user_data:
            user_instance = instance.user
            # Only allow updating specific fields of the user by the patient or admin
            allowed_user_fields_to_update = ['first_name', 'last_name', 'phone']
            for attr, value in user_data.items():
                if attr in allowed_user_fields_to_update:
                    setattr(user_instance, attr, value)
            user_instance.save()
            
        return instance

class PatientRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new User with a Patient role and creating their Patient profile.
    This is for POST /patients/ by an Admin/Doctor.
    """
    # User fields - we'll take them from the User model directly for creation
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True) 
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Patient 
        fields = [
            'email', 'password', 'first_name', 'last_name', 'phone', 
            'date_of_birth', 'gender', 'address', 'emergency_contact', 
            'insurance_provider', 'insurance_number', 'medical_history', 
            'allergies', 'current_medications'
        ]

    def validate_email(self, value):
        """
        Check that the email is not already in use.
        """
        if User.objects.filter(email__iexact=value).exists():
            # Raise with a dictionary for field-specific error
            raise serializers.ValidationError(
                {"email": "A user with this email address already exists."})
        return value
    @transaction.atomic
    def create(self, validated_data):
        user_data = {
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name'), 
            'last_name': validated_data.pop('last_name'),   
            'phone': validated_data.pop('phone', None),      
            'role': AuthUserModel.Role.PATIENT,
            'is_active': False 
        }
        user_instance = User.objects.create_user(**user_data)
        
        # Remaining validated_data is for Patient model
        patient_instance = Patient.objects.create(user=user_instance, **validated_data)

        # Send verification email to the new patient
        mail_subject = 'Activate your Etiba account.'
        uid = urlsafe_base64_encode(force_bytes(user_instance.pk))
        token = account_activation_token.make_token(user_instance) 
        # Ensure 'auth_user:verify_email' is the correct reverse lookup for your verification endpoint
        verification_link = f"{settings.SITE_URL}{reverse('auth_user:verify_email', kwargs={'uidb64': uid, 'token': token})}"
        message = f'Hi {user_instance.first_name},\n\nAn account has been created for you. Please click on the link to activate your account and set/confirm your password:\n{verification_link}'
        
        try:
            send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [user_instance.email])
        except Exception as e:
            print(f"Error sending verification email to new patient {user_instance.email}: {e}")
            # Raising a ValidationError will roll back the transaction (user and patient creation)
            # and inform the client (Admin/Doctor) about the failure.
            raise serializers.ValidationError(
                {"email_send_error": f"Could not send verification email to {user_instance.email}. Please check email server configuration or the email address. Error: {e}"}
            ) 
            
        return patient_instance
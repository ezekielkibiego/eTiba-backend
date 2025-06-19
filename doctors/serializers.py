from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

from .models import Doctor, Specialization, DoctorAvailability, DoctorSpecialization, DoctorUnavailability
from auth_user.models import User as AuthUserModel
from auth_user.utils import account_activation_token

User = get_user_model()

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    class Meta:
        model = DoctorAvailability
        fields = ['id', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time', 'break_start', 'break_end', 'is_active']
        read_only_fields = ['id', 'day_of_week_display']
        # Doctor field will be set based on the URL context
    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        # Get current or incoming values for time fields
        start_time = attrs.get('start_time', instance.start_time if instance else None)
        end_time = attrs.get('end_time', instance.end_time if instance else None)
        break_start = attrs.get('break_start', instance.break_start if instance else None)
        break_end = attrs.get('break_end', instance.break_end if instance else None)

        if start_time is not None and end_time is not None:
            if start_time >= end_time:
                raise serializers.ValidationError({"end_time": "End time must be after start time."})

            if break_start is not None and break_end is not None:
                if break_start >= break_end:
                    raise serializers.ValidationError({"break_end": "Break end time must be after break start time."})
                if not (start_time <= break_start < break_end <= end_time):
                    raise serializers.ValidationError(
                        {"break_times": "Break times must be within the working hours (start_time to end_time)."}
                    )
            elif break_start is not None and break_end is None and not (self.partial and instance and instance.break_end is not None):
                # If break_start is provided, break_end is also required, unless it's a PATCH and break_end already exists and is not being cleared.
                raise serializers.ValidationError({"break_end": "Break end time is required if break start time is provided."})
            elif break_start is None and break_end is not None and not (self.partial and instance and instance.break_start is not None):
                raise serializers.ValidationError({"break_start": "Break start time is required if break end time is provided."})

        # Validate day_of_week change for uniqueness if updating an existing instance
        if instance and 'day_of_week' in attrs and attrs['day_of_week'] != instance.day_of_week:
            new_day_of_week = attrs['day_of_week']
            doctor = instance.doctor
            if DoctorAvailability.objects.filter(doctor=doctor, day_of_week=new_day_of_week).exists():
                # This check correctly identifies a conflict if another slot for this doctor on the new day already exists.
                raise serializers.ValidationError(
                    {"day_of_week": f"An availability slot for this doctor on {dict(DoctorAvailability.WEEKDAY_CHOICES)[new_day_of_week]} already exists."}
                )
        return attrs

class DoctorUserSerializer(serializers.ModelSerializer):
    """Serializer for User fields relevant to Doctor profile display/update."""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_active']
        read_only_fields = ['id', 'email', 'is_active']

class DoctorProfileSerializer(serializers.ModelSerializer):
    user = DoctorUserSerializer()
    specializations = SpecializationSerializer(many=True, read_only=True) # Read-only for profile, managed separately if needed
    specialization_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False, allow_empty=True,
        help_text="List of Specialization UUIDs to assign to the doctor. Replaces existing specializations."
    )
    # availability_schedule = DoctorAvailabilitySerializer(many=True, read_only=True) # Availability managed via its own endpoint

    class Meta:
        model = Doctor
        fields = [
            'id', 'user', 'license_number', 'specializations', 'years_of_experience',
            'consultation_fee', 'bio', 'office_address', 'is_available', 'specialization_ids',
            'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'full_name', 'created_at', 'updated_at', 'specializations']

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        specialization_ids = validated_data.pop('specialization_ids', None)

        # Update Doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update nested User fields if present
        if user_data:
            user_instance = instance.user
            allowed_user_fields_to_update = ['first_name', 'last_name', 'phone']
            for attr, value in user_data.items():
                if attr in allowed_user_fields_to_update:
                    setattr(user_instance, attr, value)
            user_instance.save()

        # Update specializations if specialization_ids is provided in the request
        if specialization_ids is not None:
            instance.specializations.clear() # Remove all existing specializations
            if specialization_ids: # If the list is not empty, add new ones
                new_specializations = Specialization.objects.filter(id__in=specialization_ids)
                instance.specializations.add(*new_specializations)
        return instance

class DoctorRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True) # Admin sets initial password
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, write_only=True)
    specialization_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Doctor
        fields = [
            'email', 'password', 'first_name', 'last_name', 'phone', # User fields
            'license_number', 'specialization_ids', 'years_of_experience', # Doctor fields
            'consultation_fee', 'bio', 'office_address', 'is_available'
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError({"email": "A user with this email address already exists."})
        return value

    def validate_license_number(self, value):
        if Doctor.objects.filter(license_number__iexact=value).exists():
            raise serializers.ValidationError({"license_number": "This license number is already registered."})
        return value

    @transaction.atomic
    def create(self, validated_data):
        user_data = {
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'phone': validated_data.pop('phone', None),
            'role': AuthUserModel.Role.DOCTOR,
            'is_active': False # Doctors also verify email
        }
        user_instance = User.objects.create_user(**user_data)

        specialization_ids = validated_data.pop('specialization_ids', [])
        
        doctor_instance = Doctor.objects.create(user=user_instance, **validated_data)

        if specialization_ids:
            specializations = Specialization.objects.filter(id__in=specialization_ids)
            for spec in specializations:
                 DoctorSpecialization.objects.create(doctor=doctor_instance, specialization=spec)

        # Send verification email
        mail_subject = 'Activate your Etiba Doctor account.'
        uid = urlsafe_base64_encode(force_bytes(user_instance.pk))
        token = account_activation_token.make_token(user_instance)
        
        verification_link = f"{settings.SITE_URL}{reverse('auth_user:verify_email', kwargs={'uidb64': uid, 'token': token})}"
        message = f'Hi Dr. {user_instance.last_name},\n\nAn account has been created for you. Please click on the link to activate your account:\n{verification_link}'
        
        try:
            send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [user_instance.email])
        except Exception as e:
            print(f"Error sending verification email to new doctor {user_instance.email}: {e}")
            raise serializers.ValidationError(
                {"email_send_error": f"Could not send verification email to {user_instance.email}. Error: {e}"}
            )
        return doctor_instance

class DoctorUnavailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorUnavailability
        fields = ['id', 'doctor', 'start_date', 'end_date', 'reason', 'created_at']
        read_only_fields = ['id', 'doctor', 'created_at'] # Doctor will be set from URL context

    def validate(self, data):
        # Model's clean method handles start_date <= end_date
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({"end_date": "End date must be after or the same as start date."})
        return data
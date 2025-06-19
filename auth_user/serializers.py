from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from .tasks import send_verification_email_task # Import the Celery task

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")
    patient_id = serializers.SerializerMethodField()
    doctor_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'role', 'patient_id', 'doctor_id', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."}) # Corrected field name
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')

        # Extract values for specific parameters of create_user
        # User.USERNAME_FIELD is 'email'.
        email_value = validated_data.pop(User.USERNAME_FIELD) 
        password = validated_data.pop('password')
        
        # Create user but set is_active to False until email verification
        user = User.objects.create_user(
            email=email_value, # Passed to the 'email' parameter of your custom create_user
            password=password,
            is_active=False, # User is not active until verified
            **validated_data                # Other fields (first_name, last_name, role, phone)
        )

        # Send verification email asynchronously
        try:
            send_verification_email_task.delay(
                user_pk=user.pk,
                user_first_name=user.first_name,
                user_email=user.email,
                site_url=settings.SITE_URL
            )
        except Exception as e:
            # Log the error for server-side tracking
            print(f"Error queueing verification email for {user.email}: {e}")
            # Depending on your error handling strategy, you might want to
            # raise an error here or just log it if queueing failure is not critical for user creation.
        return user

    def to_representation(self, instance):
        """
        Remove patient_id and doctor_id from the output if they are None.
        """
        # Get the standard representation first
        representation = super().to_representation(instance)

        # Conditionally remove fields if their value is None
        # We use .get() and pop() with a default to safely handle cases
        # where the field might somehow not be in the representation initially
        if representation.get('patient_id') is None:
            representation.pop('patient_id', None)

        if representation.get('doctor_id') is None:
            representation.pop('doctor_id', None)

        return representation


    # The get_* methods remain the same as they calculate the potential ID or None
    def get_patient_id(self, obj):
        """
        Returns the UUID of the associated Patient profile if the user is a patient.
        """
        if obj.role == User.Role.PATIENT and hasattr(obj, 'patient_profile'):
            return obj.patient_profile.id
        return None

    def get_doctor_id(self, obj):
        """
        Returns the UUID of the associated Doctor profile if the user is a doctor.
        """
        if obj.role == User.Role.DOCTOR and hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.id
        return None

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims here if needed
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Prevent login if account is not active
        if not self.user.is_active:
            raise serializers.ValidationError({'detail': 'Account not activated. Please check your email to verify your account.'})
        # Add user details to the response
        data['user'] = UserRegistrationSerializer(self.user).data
        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, help_text="The refresh token to invalidate.")


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "No account found with this email address."})
        if user.is_active:
            raise serializers.ValidationError({"email": "This account is already active. You can proceed to login."})
        return value
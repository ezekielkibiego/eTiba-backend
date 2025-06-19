from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from .tasks import send_verification_email_task

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration. Handles password confirmation and
    initiates the account verification process.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password', 'password2', 'role')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        """Ensure the two password fields match."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        """
        Create a new user, set their account to inactive, and trigger
        the verification email.
        """
        validated_data.pop('password2')

        email_value = validated_data.pop(User.USERNAME_FIELD)
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            email=email_value,
            password=password,
            is_active=False,
            **validated_data
        )

        try:
            send_verification_email_task.delay(
                user_pk=user.pk,
                user_first_name=user.first_name,
                user_email=user.email,
                site_url=settings.SITE_URL
            )
        except Exception as e:
            print(f"Error queueing verification email for {user.email}: {e}")

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customizes the JWT token response to include user details and
    prevents inactive users from logging in.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        if not self.user.is_active:
            raise serializers.ValidationError({
                'detail': 'Account not activated. Please check your email to verify your account.'
            })
            
        data['user'] = UserRegistrationSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    """Handles the invalidation of a refresh token for user logout."""
    refresh = serializers.CharField(write_only=True, help_text="The refresh token to invalidate.")


class ResendVerificationEmailSerializer(serializers.Serializer):
    """
    Serializer for requesting a new account verification email.
    Validates that the user exists and is not already active.
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Check if the user exists and requires activation."""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "No account found with this email address."})
        
        if user.is_active:
            raise serializers.ValidationError({"email": "This account is already active. You can proceed to login."})
            
        return value

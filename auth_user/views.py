from django.contrib.auth import get_user_model
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.conf import settings
from .utils import account_activation_token
from .serializers import UserRegistrationSerializer, LogoutSerializer, CustomTokenObtainPairSerializer, ResendVerificationEmailSerializer
from .tasks import send_verification_email_task
from rest_framework.exceptions import ValidationError, NotFound, AuthenticationFailed

User = get_user_model()


@swagger_auto_schema(
    method='POST',
    operation_summary="Register a new user",
    request_body=UserRegistrationSerializer,
    responses={
        201: "User registered successfully. Please check your email to verify your account.",
        400: "Bad Request - Validation error."
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_registration_view(request):
    """
    Handle new user registration.

    Validates user data, creates an inactive user, and triggers an
    asynchronous task to send a verification email.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()  # This now triggers the email sending within the serializer
    return Response({
        "message": "User registered successfully. Please check your email to verify your account."
    }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token view to use our customized serializer.

    This extends the default JWT behavior to add user details to the
    login response and prevent inactive users from logging in.
    """
    serializer_class = CustomTokenObtainPairSerializer


@swagger_auto_schema(
    method='GET',
    operation_summary="Verify user email",
    manual_parameters=[
        openapi.Parameter('uidb64', openapi.IN_PATH, description="User ID (base64 encoded)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('token', openapi.IN_PATH, description="Activation token", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
        200: "Email verified successfully. You can now login.",
        404: "Invalid verification link: User not found.",
        400: "Invalid verification link or token has expired."
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_view(request, uidb64, token):
    """
    Activate a user account from a verification link.
    """
    try:
        # Decode the user ID from the URL.
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        # This catches various decoding errors and the case where the user doesn't exist.
        raise NotFound(detail="Invalid verification link: User not found.")

    # Check the token's validity for the user.
    if account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return Response({'message': 'Email verified successfully. You can now login.'}, status=status.HTTP_200_OK)
    
    raise ValidationError(detail="Invalid verification link or token has expired.")


@swagger_auto_schema(
    method='POST',
    operation_summary="Resend verification email",
    request_body=ResendVerificationEmailSerializer,
    responses={200: "Verification email sent successfully."}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email_view(request):
    """
    Allow a user to request a new verification email.
    """
    serializer = ResendVerificationEmailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    user = User.objects.get(email=email) # Serializer has already confirmed the user exists and is inactive.

    # Offload email sending to a background worker.
    try:
        send_verification_email_task.delay(
            user_pk=user.pk,
            user_first_name=user.first_name,
            user_email=user.email,
            site_url=settings.SITE_URL,
            mail_subject_prefix="Resend: " # Provide context that this is a resent email.
        )
        return Response({'message': 'Verification email sent successfully.'}, status=status.HTTP_200_OK)
    except Exception as e:
        # This handles cases where the message broker (e.g., RabbitMQ, Redis) is down.
        print(f"Error queueing resend verification email for {user.email}: {e}")
        # Let the global exception handler manage this as a server error.
        raise


@swagger_auto_schema(
    method='POST',
    operation_summary="Logout user",
    request_body=LogoutSerializer,
    responses={
        200: "Logout successful.",
        400: "Refresh token not provided.",
        401: "Invalid or expired token."
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout_view(request):
    """
    Securely log out a user by blacklisting their refresh token.
    """
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()
        return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)
    except TokenError:
        # This occurs if the token is malformed, expired, or already blacklisted.
        raise AuthenticationFailed(detail="Invalid or expired token.")
    except Exception as e:
        # A catch-all for unexpected errors.
        print(f"Unexpected error during logout: {e}")
        raise

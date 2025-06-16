from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model

from .utils import account_activation_token

@shared_task(bind=True, max_retries=3)
def send_verification_email_task(self, user_pk, user_first_name, user_email, site_url, mail_subject_prefix=""):
    """Asynchronous Celery task to send a user verification email with retry logic."""
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        # User was deleted before the task could run.
        print(f"User with pk {user_pk} not found. Aborting verification email.")
        return

    # Generate the secure verification link.
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    path = reverse('auth_user:verify_email', kwargs={'uidb64': uid, 'token': token})
    verification_link = f"{site_url.rstrip('/')}{path}"  
    
    # For dev debugging.
    print(verification_link)

    # Prepare and send the email.
    mail_subject = f"{mail_subject_prefix}Activate your Etiba account"
    message = (
        f"Hi {user_first_name},\n\n"
        f"Please click the link below to confirm your registration:\n\n"
        f"{verification_link}\n\n"
        f"If you did not sign up, please ignore this email.\n\n"
        f"Thank you!"
    )

    try:
        send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])
    except Exception as e:
        # Retry sending the email on failure.
        print(f"Failed to send verification email to {user_email}: {e}. Retrying...")
        raise self.retry(exc=e, countdown=60)

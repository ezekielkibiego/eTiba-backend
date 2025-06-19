from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import Notification
# We'll need the Appointment model to fetch details
# Assuming your appointment model is in an 'appointments' app
# from appointments.models import Appointment

User = get_user_model()

@shared_task(bind=True, max_retries=3)
def create_generic_notification_task(self, recipient_id, verb, description=None,
                             actor_content_type_id=None, actor_object_id=None,
                             target_content_type_id=None, target_object_id=None,
                             action_object_content_type_id=None, action_object_object_id=None):
    """
    Asynchronously creates a notification.
    Object IDs should be passed as strings if they are UUIDs.
    """
    try:
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        print(f"Recipient User with ID {recipient_id} not found. Notification not created.")
        return

    notification_data = {
        'recipient': recipient,
        'verb': verb,
        'description': description,
    }

    if actor_content_type_id and actor_object_id:
        notification_data['actor_content_type_id'] = actor_content_type_id
        notification_data['actor_object_id'] = str(actor_object_id)
    if target_content_type_id and target_object_id:
        notification_data['target_content_type_id'] = target_content_type_id
        notification_data['target_object_id'] = str(target_object_id)
    if action_object_content_type_id and action_object_object_id:
        notification_data['action_object_content_type_id'] = action_object_content_type_id
        notification_data['action_object_object_id'] = str(action_object_object_id)

    print(f"Attempting to create notification with data: {notification_data}") # Log data before creation
    try:
        Notification.objects.create(**notification_data)
        print(f"Successfully created notification for recipient {recipient_id}, verb: {verb}") # Log success
    except Exception as e:
        print(f"Error creating notification for recipient {recipient_id}: {e}")
        raise self.retry(exc=e, countdown=60) # Retry after 60 seconds

@shared_task(bind=True, max_retries=3)
def create_appointment_creation_notification_task(self, appointment_id, actor_user_id):
    """
    Asynchronously creates notifications for patient and doctor when an appointment is made.
    """
    # Import here to avoid circular dependencies at module load time
    from appointments.models import Appointment # Adjust if your model is elsewhere

    try:
        appointment = Appointment.objects.select_related(
            'patient__user', 
            'doctor__user'
        ).get(pk=appointment_id)
    except Appointment.DoesNotExist:
        print(f"Appointment with ID {appointment_id} not found. Notification not created.")
        return

    try:
        actor = User.objects.get(pk=actor_user_id)
    except User.DoesNotExist:
        print(f"Actor User with ID {actor_user_id} not found. Using system as actor.")
        actor = None # Or handle as an error

    patient_user = appointment.patient.user
    doctor_user = appointment.doctor.user

    appointment_ct = ContentType.objects.get_for_model(appointment)
    actor_ct = ContentType.objects.get_for_model(actor) if actor else None

    # Notification for Patient
    create_generic_notification_task.delay(
        recipient_id=str(patient_user.id),
        verb=f"Appointment Scheduled with Dr. {doctor_user.last_name}",
        description=f"Your appointment for '{appointment.reason}' on {appointment.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} has been confirmed.",
        actor_content_type_id=actor_ct.id if actor_ct else None,
        actor_object_id=str(actor.id) if actor else None,
        action_object_content_type_id=appointment_ct.id,
        action_object_object_id=str(appointment.id)
    )

    # Notification for Doctor
    create_generic_notification_task.delay(
        recipient_id=str(doctor_user.id),
        verb=f"New Appointment with {patient_user.get_full_name()}",
        description=f"A new appointment for '{appointment.reason}' has been scheduled for {appointment.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}.",
        actor_content_type_id=actor_ct.id if actor_ct else None,
        actor_object_id=str(actor.id) if actor else None,
        action_object_content_type_id=appointment_ct.id,
        action_object_object_id=str(appointment.id)
    )

@shared_task(bind=True, max_retries=3)
def create_appointment_change_notification_task(self, appointment_id, actor_user_id,
                                                patient_verb, doctor_verb,
                                                patient_description, doctor_description):
    """
    Asynchronously creates notifications for patient and doctor when an appointment is changed.
    """
    from appointments.models import Appointment # Local import to avoid circular dependencies

    try:
        appointment = Appointment.objects.select_related(
            'patient__user', 
            'doctor__user'
        ).get(pk=appointment_id)
    except Appointment.DoesNotExist:
        print(f"Appointment with ID {appointment_id} not found for change notification. Notification not created.")
        return

    actor = None
    if actor_user_id:
        try:
            actor = User.objects.get(pk=actor_user_id)
        except User.DoesNotExist:
            print(f"Actor User with ID {actor_user_id} not found for change notification.")
            # Actor is optional, so we can proceed. The generic task handles None actor.

    patient_user = appointment.patient.user
    doctor_user = appointment.doctor.user

    appointment_ct = ContentType.objects.get_for_model(appointment)
    actor_ct = ContentType.objects.get_for_model(actor) if actor else None
    actor_id_str = str(actor.id) if actor else None
    
    # Notification for Patient
    create_generic_notification_task.delay(
        recipient_id=str(patient_user.id), verb=patient_verb, description=patient_description,
        actor_content_type_id=actor_ct.id if actor_ct else None, actor_object_id=actor_id_str,
        action_object_content_type_id=appointment_ct.id, action_object_object_id=str(appointment.id))
    # Notification for Doctor
    create_generic_notification_task.delay(
        recipient_id=str(doctor_user.id), verb=doctor_verb, description=doctor_description,
        actor_content_type_id=actor_ct.id if actor_ct else None, actor_object_id=actor_id_str,
        action_object_content_type_id=appointment_ct.id, action_object_object_id=str(appointment.id))
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    
    # Actor (optional, who performed the action)
    actor_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='actor_notifications')
    actor_object_id = models.CharField(max_length=255, null=True, blank=True) # Changed from UUIDField to CharField for flexibility
    actor = GenericForeignKey('actor_content_type', 'actor_object_id')

    verb = models.CharField(max_length=255) # e.g., "created appointment", "updated appointment status"
    
    # Target (optional, the object the action was performed on, if different from action_object)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='target_notifications')
    target_object_id = models.CharField(max_length=255, null=True, blank=True) # Changed from UUIDField to CharField for flexibility
    target = GenericForeignKey('target_content_type', 'target_object_id')

    # Action Object (optional, the primary object related to the notification, e.g., an Appointment)
    action_object_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='action_object_notifications')
    action_object_object_id = models.CharField(max_length=255, null=True, blank=True) # Changed from UUIDField to CharField for flexibility
    action_object = GenericForeignKey('action_object_content_type', 'action_object_object_id')
    
    description = models.TextField(blank=True, null=True) # A human-readable description
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        db_table = 'notifications'

    def __str__(self):
        return f"Notification for {self.recipient.email} - {self.verb}"
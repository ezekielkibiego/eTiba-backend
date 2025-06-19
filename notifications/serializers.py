from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Notification
from auth_user.serializers import UserRegistrationSerializer # For recipient display

# A generic serializer for related objects (actor, target, action_object)
# This is a simplified version. You might want specific serializers for common types.
class GenericRelatedObjectSerializer(serializers.RelatedField):
    def to_representation(self, value):
        if value is None:
            return None
        if hasattr(value, 'get_absolute_url'): # Example: if your models have this
            return {'id': str(value.id), 'type': ContentType.objects.get_for_model(value).model, 'url': value.get_absolute_url()}
        return {'id': str(value.id), 'type': ContentType.objects.get_for_model(value).model, 'str': str(value)}

class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserRegistrationSerializer(read_only=True) # Display recipient details
    actor = GenericRelatedObjectSerializer(read_only=True)
    target = GenericRelatedObjectSerializer(read_only=True)
    action_object = GenericRelatedObjectSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'actor', 'verb', 'target', 
            'action_object', 'description', 'read', 'timestamp'
        ]
        read_only_fields = [
            'id', 'recipient', 'actor', 'verb', 'target', 
            'action_object', 'description', 'timestamp'
        ] # 'read' status can be updated

class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['read'] # Only allow updating the 'read' status
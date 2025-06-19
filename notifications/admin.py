from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'verb', 'read', 'timestamp', 'actor', 'target', 'action_object')
    list_filter = ('read', 'timestamp', 'recipient', 'verb')
    search_fields = ('recipient__email', 'verb', 'description')
    readonly_fields = ('timestamp', 'actor_content_type', 'actor_object_id', 'target_content_type', 'target_object_id', 'action_object_content_type', 'action_object_object_id')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'actor_content_type', 'target_content_type', 'action_object_content_type')
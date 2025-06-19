from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Notification
from .serializers import NotificationSerializer, NotificationUpdateSerializer

@swagger_auto_schema(
    method='GET',
    operation_summary="List user's notifications",
    operation_description="Retrieves a paginated list of notifications for the authenticated user.",
    manual_parameters=[
        openapi.Parameter('read', openapi.IN_QUERY, description="Filter by read status (true/false)", type=openapi.TYPE_BOOLEAN),
    ],
    responses={200: NotificationSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    queryset = Notification.objects.filter(recipient=request.user).select_related(
        'actor_content_type', 'target_content_type', 'action_object_content_type'
    ) # Optimize queries

    read_status_query = request.query_params.get('read')
    if read_status_query is not None:
        if read_status_query.lower() == 'true':
            queryset = queryset.filter(read=True)
        elif read_status_query.lower() == 'false':
            queryset = queryset.filter(read=False)

    paginator = PageNumberPagination()
    paginator.page_size = 15
    result_page = paginator.paginate_queryset(queryset, request)
    serializer = NotificationSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='PATCH',
    operation_summary="Mark a notification as read/unread",
    request_body=NotificationUpdateSerializer,
    responses={
        200: NotificationSerializer,
        404: "Notification not found"
    }
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_notification_status(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
    except Notification.DoesNotExist:
        return Response({"detail": "Notification not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    serializer = NotificationUpdateSerializer(notification, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        # Return the full notification object after update
        return Response(NotificationSerializer(notification, context={'request': request}).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
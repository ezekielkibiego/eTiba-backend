from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction # Import transaction
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.pagination import PageNumberPagination # Import PageNumberPagination

from .models import Appointment, AppointmentStatusHistory
from .serializers import (
    AppointmentSerializer, AppointmentStatusUpdateSerializer, 
    AvailabilityCheckSerializer
)
from .permissions import IsOwnerOrDoctorOrAdmin, CanCreateAppointment, IsAdminOrReadOnly
from .services import AppointmentService
from auth_user.models import User as AuthUserModel
from notifications.tasks import create_appointment_change_notification_task # Import the new task

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default number of items per page
    page_size_query_param = 'page_size' # Allow client to override page_size
    max_page_size = 100 # Maximum limit for page_size

class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, CanCreateAppointment]
    pagination_class = StandardResultsSetPagination # Add this line to enable pagination

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related('patient__user', 'doctor__user').prefetch_related('status_history').all()

        if user.role == AuthUserModel.Role.PATIENT:
            queryset = queryset.filter(patient__user=user)
        elif user.role == AuthUserModel.Role.DOCTOR:
            queryset = queryset.filter(doctor__user=user)
        elif not user.is_staff: # Should not happen if permissions are set right
            return queryset.none()
        
        # Add filtering parameters (e.g., date_range, status)
        status_param = self.request.query_params.get('status')
        date_from_param = self.request.query_params.get('date_from')
        date_to_param = self.request.query_params.get('date_to')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if date_from_param:
            queryset = queryset.filter(appointment_datetime__gte=date_from_param)
        if date_to_param:
            queryset = queryset.filter(appointment_datetime__lte=date_to_param)
            
        return queryset.order_by('-appointment_datetime')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), CanCreateAppointment()]
        return [IsAuthenticated()] # For GET, further filtering by role in get_queryset

    @swagger_auto_schema(
        operation_summary="List appointments (filtered by role) or create a new one.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by appointment status", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, description="Filter appointments from this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, description="Filter appointments up to this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Create a new appointment.")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class AppointmentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.select_related('patient__user', 'doctor__user').prefetch_related('status_history').all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrDoctorOrAdmin]

    @swagger_auto_schema(operation_summary="Get specific appointment details.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update an existing appointment.")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Partially update an existing appointment.")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Cancel an appointment (sets status to 'cancelled').",
        responses={200: AppointmentSerializer}
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_be_cancelled:
            return Response(
                {"detail": "This appointment cannot be cancelled (e.g., it's in the past or already completed/cancelled)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        original_status = instance.status
        instance.status = 'cancelled' # Directly use the status string value
        instance.save()

        AppointmentStatusHistory.objects.create(
            appointment=instance,
            previous_status=original_status,
            new_status=instance.status,
            changed_by=request.user,
            reason=request.data.get('reason', "Cancelled by user.")
        )
        
        # Trigger notification for cancellation
        actor_user = request.user
        actor_user_id_str = str(actor_user.id)
        cancelled_reason = request.data.get('reason', "Cancelled by user.")

        patient_verb = "Appointment Cancelled"
        doctor_verb = f"Appointment Cancelled for {instance.patient.user.get_full_name()}"

        patient_description = f"Your appointment with Dr. {instance.doctor.user.last_name} on {instance.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} has been cancelled."
        if cancelled_reason and cancelled_reason != "Cancelled by user.":
            patient_description += f" Reason: {cancelled_reason}"
        doctor_description = f"The appointment for {instance.patient.user.get_full_name()} on {instance.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} has been cancelled by {actor_user.get_full_name()}."
        if cancelled_reason and cancelled_reason != "Cancelled by user.":
            doctor_description += f" Reason: {cancelled_reason}"

        transaction.on_commit(
            lambda: create_appointment_change_notification_task.delay(
                appointment_id=str(instance.id), actor_user_id=actor_user_id_str,
                patient_verb=patient_verb, doctor_verb=doctor_verb,
                patient_description=patient_description, doctor_description=doctor_description
            )
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@swagger_auto_schema(
    method='PATCH',
    operation_summary="Update appointment status.",
    request_body=AppointmentStatusUpdateSerializer,
    responses={200: AppointmentSerializer, 400: "Bad Request", 403: "Permission Denied"}
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsOwnerOrDoctorOrAdmin]) # Ensure IsOwnerOrDoctorOrAdmin checks if user can change status
def update_appointment_status_view(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Explicit permission check for status update logic (e.g. patient can only cancel)
    # IsOwnerOrDoctorOrAdmin provides base object permission.
    # More granular logic might be needed here based on roles and target status.
    # For example, a patient might only be allowed to change status to 'cancelled'.
    # A doctor might change it to 'completed', 'in_progress', 'no_show'.

    serializer = AppointmentStatusUpdateSerializer(data=request.data)
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason')

        # Patient can only change status to 'cancelled'
        if request.user.role == AuthUserModel.Role.PATIENT and new_status != 'cancelled':
             return Response({"detail": "Patients can only cancel appointments."}, status=status.HTTP_403_FORBIDDEN)

        original_status = appointment.status
        appointment.status = new_status
        appointment.save()

        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            previous_status=original_status,
            new_status=new_status,
            changed_by=request.user,
            reason=reason
        )
        
        # Trigger notification for status update
        actor_user = request.user
        actor_user_id_str = str(actor_user.id)

        patient_verb = "Appointment Status Updated"
        doctor_verb = f"Appointment Status Updated for {appointment.patient.user.get_full_name()}"

        patient_description = f"The status of your appointment with Dr. {appointment.doctor.user.last_name} on {appointment.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} has been changed from '{original_status}' to '{new_status}'."
        if reason:
            patient_description += f" Reason: {reason}"
        doctor_description = f"The status of the appointment for {appointment.patient.user.get_full_name()} on {appointment.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} has been changed from '{original_status}' to '{new_status}' by {actor_user.get_full_name()}."
        if reason:
            doctor_description += f" Reason: {reason}"

        transaction.on_commit(
            lambda: create_appointment_change_notification_task.delay(
                appointment_id=str(appointment.id), actor_user_id=str(request.user.id),
                patient_verb=patient_verb, doctor_verb=doctor_verb,
                patient_description=patient_description, doctor_description=doctor_description
            )
        )

        response_serializer = AppointmentSerializer(appointment, context={'request': request})
        return Response(response_serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='GET',
    operation_summary="Check doctor's availability for booking.",
    query_serializer=AvailabilityCheckSerializer,
    responses={200: openapi.Response("List of available time slots", examples={"application/json": {"available_slots": ["09:00:00", "10:00:00"]}})}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Any authenticated user can check
def check_availability_view(request):
    serializer = AvailabilityCheckSerializer(data=request.query_params)
    if serializer.is_valid():
        doctor_id = serializer.validated_data['doctor_id']
        date = serializer.validated_data['date']
        duration = serializer.validated_data['duration']
        
        # Use the service to get available slots
        # This is a placeholder for a more complex implementation
        available_slots = AppointmentService.get_available_slots(doctor_id, date, duration)
        return Response({"available_slots": available_slots})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
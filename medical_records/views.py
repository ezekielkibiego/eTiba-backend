from rest_framework import generics, status, parsers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import MedicalRecord, MedicalRecordAttachment
from .serializers import MedicalRecordSerializer, MedicalRecordAttachmentSerializer
from .permissions import IsDoctorUser, CanViewMedicalRecord, IsRecordCreatorOrAdmin
from auth_user.models import User as AuthUserModel
from appointments.views import StandardResultsSetPagination # Assuming you have this

class MedicalRecordListCreateView(generics.ListCreateAPIView):
    serializer_class = MedicalRecordSerializer
    pagination_class = StandardResultsSetPagination # Add pagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsDoctorUser()] # Only doctors can create
        return [IsAuthenticated()] # Listing requires further filtering in get_queryset

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return MedicalRecord.objects.select_related('patient__user', 'doctor__user', 'created_by').prefetch_related('attachments').all()
        elif user.role == AuthUserModel.Role.PATIENT and hasattr(user, 'patient_profile'):
            return MedicalRecord.objects.select_related('patient__user', 'doctor__user', 'created_by').prefetch_related('attachments').filter(patient=user.patient_profile)
        elif user.role == AuthUserModel.Role.DOCTOR and hasattr(user, 'doctor_profile'):
            # Doctors see records they created or records of patients linked to their appointments (more complex query)
            # For simplicity now, let's show records they created.
            # A more advanced filter could involve checking appointments.
            return MedicalRecord.objects.select_related('patient__user', 'doctor__user', 'created_by').prefetch_related('attachments').filter(doctor=user.doctor_profile)
        return MedicalRecord.objects.none()

    @swagger_auto_schema(
        operation_summary="List medical records",
        operation_description="Lists medical records based on user role. Patients see their own, Doctors see records they created (or are associated with, depending on full logic), Admins see all.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a medical record",
        operation_description="Allows authenticated doctors to create a new medical record.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class MedicalRecordRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MedicalRecordSerializer
    queryset = MedicalRecord.objects.select_related('patient__user', 'doctor__user', 'created_by').prefetch_related('attachments').all()
    permission_classes = [IsAuthenticated] # Base permission, object-level checked below

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # Only the creating doctor or admin can update/delete
            return [IsAuthenticated(), IsRecordCreatorOrAdmin()]
        # For GET, more granular permission
        return [IsAuthenticated(), CanViewMedicalRecord()]

    @swagger_auto_schema(operation_summary="Retrieve a medical record")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update a medical record")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Partially update a medical record")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete a medical record (Soft Delete)")
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete() # Using soft delete
        return Response(status=status.HTTP_204_NO_CONTENT)


class MedicalRecordAttachmentUploadView(generics.CreateAPIView):
    serializer_class = MedicalRecordAttachmentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    permission_classes = [IsAuthenticated, IsDoctorUser] # Or more specific based on who can update record

    @swagger_auto_schema(
        operation_summary="Upload an attachment to a medical record",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, description="File to upload", type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('description', openapi.IN_FORM, description="Optional description for the file", type=openapi.TYPE_STRING)
        ]
    )
    def post(self, request, record_pk, *args, **kwargs):
        medical_record = get_object_or_404(MedicalRecord, pk=record_pk)

        # Check if user has permission to add attachment to this specific record
        # (e.g., if they are the doctor who created the record or an admin)
        permission_checker = IsRecordCreatorOrAdmin()
        if not permission_checker.has_object_permission(request, self, medical_record):
             return Response({"detail": "You do not have permission to add attachments to this record."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(medical_record=medical_record, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MedicalRecordAttachmentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = MedicalRecordAttachmentSerializer
    permission_classes = [IsAuthenticated] # Object permissions handled below

    def get_queryset(self):
        # Ensure attachment belongs to the specified medical record
        return MedicalRecordAttachment.objects.filter(medical_record_id=self.kwargs.get('record_pk'))

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs.get('attachment_pk'))
        # Check permission to view/delete based on the parent medical record
        medical_record = obj.medical_record
        permission_checker = CanViewMedicalRecord() if self.request.method == 'GET' else IsRecordCreatorOrAdmin()
        if not permission_checker.has_object_permission(self.request, self, medical_record):
            self.permission_denied(self.request, message="You do not have permission to access this attachment.")
        return obj

    @swagger_auto_schema(operation_summary="Delete a medical record attachment")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs) # Hard delete for attachments for now
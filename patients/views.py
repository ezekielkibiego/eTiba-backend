from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.pagination import PageNumberPagination 
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.exceptions import PermissionDenied 
from .models import Patient
from .serializers import PatientProfileSerializer, PatientRegistrationSerializer 
from .permissions import IsAdminOrDoctor, IsPatientUserRole, IsOwnerOrAdminOrDoctorReadOnlyForPatient
from .filters import PatientFilter 
from auth_user.models import User as AuthUserModel 

User = get_user_model()

@swagger_auto_schema(
    method='GET',
    operation_summary="List all patients",
    operation_description="Retrieves a paginated list of all patient profiles with search and filtering. (Admin/Doctor only)",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search term for patient's name, email, address, medical info, insurance.", type=openapi.TYPE_STRING),
        openapi.Parameter('gender', openapi.IN_QUERY, description="Filter by gender (M, F, O, P)", type=openapi.TYPE_STRING, enum=['M', 'F', 'O', 'P']),
        openapi.Parameter('date_of_birth', openapi.IN_QUERY, description="Filter by date of birth (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        openapi.Parameter('date_of_birth__year', openapi.IN_QUERY, description="Filter by year of birth", type=openapi.TYPE_INTEGER),
        openapi.Parameter('address__icontains', openapi.IN_QUERY, description="Filter by partial address (case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('phone', openapi.IN_QUERY, description="Filter by patient's phone number (contains, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('insurance_provider__icontains', openapi.IN_QUERY, description="Filter by partial insurance provider (case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('insurance_number__iexact', openapi.IN_QUERY, description="Filter by insurance number (exact, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('first_name', openapi.IN_QUERY, description="Filter by patient's first name (contains, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('last_name', openapi.IN_QUERY, description="Filter by patient's last name (contains, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('email', openapi.IN_QUERY, description="Filter by patient's email (exact, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('medical_history__icontains', openapi.IN_QUERY, description="Search in medical history (contains, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('allergies__icontains', openapi.IN_QUERY, description="Search in allergies (contains, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('current_medications__icontains', openapi.IN_QUERY, description="Search in current medications (contains, case-insensitive)", type=openapi.TYPE_STRING),
    ],
    responses={200: PatientProfileSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAdminOrDoctor])
def list_patients(request):
    # Define search_fields and filterset_class as attributes of the view function
    list_patients.search_fields = [
        'user__first_name', 'user__last_name', 'user__email', 'user__phone',
        'address', 'medical_history', 'allergies', 'current_medications',
        'insurance_provider', 'insurance_number', 'emergency_contact'
    ]
    list_patients.filterset_class = PatientFilter

    queryset = Patient.objects.select_related('user').all().order_by('user__last_name', 'user__first_name', '-created_at')
    
    # Apply filtering and search
    filter_backends_tuple = (DjangoFilterBackend, SearchFilter)

    for backend_class in filter_backends_tuple:
        backend_instance = backend_class()
        # The backend instance will look for filterset_class and search_fields on the 'view' object (list_patients)
        queryset = backend_instance.filter_queryset(request, queryset, view=list_patients)
    
    paginator = PageNumberPagination()
    paginator.page_size = 10 
    result_page = paginator.paginate_queryset(queryset, request)
    
    serializer = PatientProfileSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='POST',
    operation_summary="Register a new patient",
    operation_description="Creates a new user with a patient role and their patient profile. (Admin/Doctor only)",
    request_body=PatientRegistrationSerializer,
    responses={
        201: PatientProfileSerializer,
        400: "Bad Request - Validation Error"
    }
)
@api_view(['POST'])
@permission_classes([IsAdminOrDoctor])
def register_patient(request):
    serializer = PatientRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        patient_instance = serializer.save()
        # To return the full profile after creation, re-serialize with PatientProfileSerializer
        profile_serializer = PatientProfileSerializer(patient_instance, context={'request': request})
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='GET',
    operation_summary="Get specific patient profile",
    operation_description="Retrieves details of a specific patient. (Owner/Admin/Doctor-Readonly)",
    responses={
        200: PatientProfileSerializer,
        404: "Patient not found"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def retrieve_patient(request, pk):
    patient = get_object_or_404(Patient.objects.select_related('user'), pk=pk)
    # Manually check object-level permission
    permission_checker = IsOwnerOrAdminOrDoctorReadOnlyForPatient()
    if not permission_checker.has_object_permission(request, None, patient):
        raise PermissionDenied(detail='You do not have permission to perform this action.')
    serializer = PatientProfileSerializer(patient, context={'request': request})
    return Response(serializer.data)

@swagger_auto_schema(
    method='PUT',
    operation_summary="Update patient profile",
    operation_description="Updates details of a specific patient. (Owner/Admin only)",
    request_body=PatientProfileSerializer,
    responses={
        200: PatientProfileSerializer,
        400: "Bad Request - Validation Error",
        404: "Patient not found"
    }
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated]) 
def update_patient(request, pk):
    patient = get_object_or_404(Patient.objects.select_related('user'), pk=pk)
    permission_checker = IsOwnerOrAdminOrDoctorReadOnlyForPatient()
    if not permission_checker.has_object_permission(request, None, patient):
        raise PermissionDenied(detail='You do not have permission to perform this action.')
    
    # Doctors cannot update
    if request.user.role == AuthUserModel.Role.DOCTOR and request.user != patient.user:
         raise PermissionDenied(detail='Doctors can only view patient profiles.')

    partial = request.method == 'PATCH'
    serializer = PatientProfileSerializer(patient, data=request.data, partial=partial, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='DELETE',
    operation_summary="Deactivate patient account",
    operation_description="Deactivates the user account associated with the patient. (Admin only)",
    responses={
        200: openapi.Response(
            description="Patient account deactivated successfully.",
            examples={"application/json": {"message": "Patient account deactivated successfully."}}
        ),
        404: "Patient not found"
    }
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deactivate_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    user_to_deactivate = patient.user
    user_to_deactivate.is_active = False
    user_to_deactivate.save()
    return Response({"message": "Patient account deactivated successfully."}, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='GET',
    operation_summary="Get current patient's profile",
    operation_description="Retrieves the profile of the currently authenticated patient.",
    responses={200: PatientProfileSerializer}
)
@swagger_auto_schema(
    method='PUT',
    operation_summary="Update current patient's profile",
    operation_description="Updates the profile of the currently authenticated patient.",
    request_body=PatientProfileSerializer,
    responses={200: PatientProfileSerializer}
)
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsPatientUserRole])
def patient_me_profile(request):
    patient_profile = get_object_or_404(Patient.objects.select_related('user'), user=request.user)
    if request.method == 'GET':
        serializer = PatientProfileSerializer(patient_profile, context={'request': request})
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = PatientProfileSerializer(patient_profile, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

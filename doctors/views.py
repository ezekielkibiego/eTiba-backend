from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter # Import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend # Import DjangoFilterBackend
from django.db import transaction # Import transaction

from .models import Doctor, Specialization, DoctorAvailability
from .serializers import ( # Add DoctorUnavailabilitySerializer
    DoctorProfileSerializer, DoctorRegistrationSerializer, 
    SpecializationSerializer, DoctorAvailabilitySerializer, DoctorUnavailabilitySerializer
)
from .permissions import IsAdminUser as IsAdminRole, IsOwnerOrAdminForDoctor # Renamed for clarity
from .filters import DoctorFilter # Ensure DoctorFilter is imported at the module level
from auth_user.models import User as AuthUserModel
from rest_framework.exceptions import PermissionDenied

User = get_user_model()

@swagger_auto_schema(method='GET', responses={200: SpecializationSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Any authenticated user can see specializations
def list_specializations(request):
    specializations = Specialization.objects.all().order_by('name')
    paginator = PageNumberPagination()
    paginator.page_size = 20
    result_page = paginator.paginate_queryset(specializations, request)
    serializer = SpecializationSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='GET',
    operation_summary="List all active doctors with search and filtering",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search term for doctor's name, email, license, bio", type=openapi.TYPE_STRING),
        openapi.Parameter('is_available', openapi.IN_QUERY, description="Filter by availability (true/false)", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('available_from', openapi.IN_QUERY, description="Filter by doctors available from a specific date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        openapi.Parameter('office_address__icontains', openapi.IN_QUERY, description="Filter by partial office address (case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('specialization_name', openapi.IN_QUERY, description="Filter by specialization name (exact, case-insensitive)", type=openapi.TYPE_STRING),
        openapi.Parameter('specialization_id', openapi.IN_QUERY, description="Filter by specialization UUID", type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        openapi.Parameter('years_of_experience', openapi.IN_QUERY, description="Filter by exact years of experience", type=openapi.TYPE_INTEGER),
        openapi.Parameter('years_of_experience__gte', openapi.IN_QUERY, description="Filter by minimum years of experience", type=openapi.TYPE_INTEGER),
        openapi.Parameter('years_of_experience__lte', openapi.IN_QUERY, description="Filter by maximum years of experience", type=openapi.TYPE_INTEGER),
        openapi.Parameter('consultation_fee', openapi.IN_QUERY, description="Filter by exact consultation fee", type=openapi.TYPE_NUMBER),
        openapi.Parameter('consultation_fee__gte', openapi.IN_QUERY, description="Filter by minimum consultation fee", type=openapi.TYPE_NUMBER),
        openapi.Parameter('consultation_fee__lte', openapi.IN_QUERY, description="Filter by maximum consultation fee", type=openapi.TYPE_NUMBER),
        openapi.Parameter('phone', openapi.IN_QUERY, description="Filter by doctor's phone number (contains, case-insensitive)", type=openapi.TYPE_STRING),
    ],
    responses={200: DoctorProfileSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Any authenticated user can list doctors
def list_doctors(request):
    # Define search_fields and filterset_class as attributes of the view function
    list_doctors.search_fields = [
        'user__first_name', 'user__last_name', 'user__email', 'user__phone',
        'license_number', 'bio', 'office_address', 'specializations__name', 'specializations__description'
    ]
    list_doctors.filterset_class = DoctorFilter

    queryset = Doctor.objects.select_related('user').prefetch_related('specializations', 'unavailable_dates').filter(user__is_active=True).order_by('user__last_name', 'user__first_name')

    # Apply filtering and search
    filter_backends_tuple = (DjangoFilterBackend, SearchFilter)
    for backend_class in filter_backends_tuple:
        backend_instance = backend_class()
        queryset = backend_instance.filter_queryset(request, queryset, view=list_doctors)
    doctors = queryset
    paginator = PageNumberPagination()
    paginator.page_size = 10
    result_page = paginator.paginate_queryset(doctors, request)
    serializer = DoctorProfileSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(method='POST', request_body=DoctorRegistrationSerializer, responses={201: DoctorProfileSerializer})
@api_view(['POST'])
@permission_classes([IsAdminRole]) # Only Admin can register new doctors
def register_doctor(request):
    serializer = DoctorRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        doctor_instance = serializer.save()
        profile_serializer = DoctorProfileSerializer(doctor_instance, context={'request': request})
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='GET', responses={200: DoctorProfileSerializer})
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Any authenticated user can view a doctor's profile
def retrieve_doctor(request, pk):
    doctor = get_object_or_404(Doctor.objects.select_related('user').prefetch_related('specializations'), pk=pk)
    serializer = DoctorProfileSerializer(doctor, context={'request': request})
    return Response(serializer.data)

@swagger_auto_schema(method='PUT', request_body=DoctorProfileSerializer, responses={200: DoctorProfileSerializer})
@api_view(['PUT', 'PATCH'])
@permission_classes([IsOwnerOrAdminForDoctor])
def update_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    # Permission class IsOwnerOrAdminForDoctor handles object-level permission
    partial = request.method == 'PATCH'
    serializer = DoctorProfileSerializer(doctor, data=request.data, partial=partial, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='DELETE', responses={200: openapi.Response("Doctor account deactivated")})
@api_view(['DELETE'])
@permission_classes([IsAdminRole]) # Only Admin can deactivate
def deactivate_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    user_to_deactivate = doctor.user
    user_to_deactivate.is_active = False
    user_to_deactivate.save()
    return Response({"message": "Doctor account deactivated successfully."}, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='GET',
    operation_summary="List doctor's active availability slots (paginated)",
    responses={200: DoctorAvailabilitySerializer(many=True)} # Swagger might not show pagination structure by default here
)
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Any authenticated user can see availability
def get_doctor_availability(request, doctor_pk): # Changed pk to doctor_pk
    doctor = get_object_or_404(Doctor, pk=doctor_pk, user__is_active=True)
    availability = DoctorAvailability.objects.filter(doctor=doctor, is_active=True).order_by('day_of_week', 'start_time')
    
    paginator = PageNumberPagination()
    paginator.page_size = 7 # Max 7 days in a week, but good for consistency
    result_page = paginator.paginate_queryset(availability, request)
    serializer = DoctorAvailabilitySerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='PUT',
    request_body=DoctorAvailabilitySerializer(many=True), # Expects a list of availability slots
    responses={200: DoctorAvailabilitySerializer(many=True)}
)
@api_view(['PUT'])
@permission_classes([IsOwnerOrAdminForDoctor]) # Doctor or Admin can update availability
def update_doctor_availability(request, doctor_pk): # Changed pk to doctor_pk
    doctor = get_object_or_404(Doctor, pk=doctor_pk)
    # Check object permission for the doctor profile itself
    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, update_doctor_availability, doctor): # Pass view for context
        raise PermissionDenied(detail='You do not have permission to update this doctor\'s availability.')

    # Expects a list of availability slots. This will replace all existing active slots.
    serializer = DoctorAvailabilitySerializer(data=request.data, many=True, context={'request': request})
    if serializer.is_valid():
        with transaction.atomic():
            # Delete old availability slots for this doctor before creating new ones
            DoctorAvailability.objects.filter(doctor=doctor).delete()

            processed_days = set()
            new_availability_slots = []
            # Iterate in reverse to keep the last occurrence of a duplicate day_of_week
            for slot_data in reversed(serializer.validated_data):
                day = slot_data.get('day_of_week')
                if day in processed_days:
                    continue # Skip if this day_of_week has already been processed
                
                slot_data['doctor'] = doctor # Ensure doctor is set
                slot_data['is_active'] = True
                new_slot = DoctorAvailability.objects.create(**slot_data)
                new_availability_slots.insert(0, new_slot) # Insert at beginning to maintain original order
                processed_days.add(day)
        response_serializer = DoctorAvailabilitySerializer(sorted(new_availability_slots, key=lambda x: x.day_of_week), many=True, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='GET',
    operation_summary="Retrieve a specific availability slot",
    responses={200: DoctorAvailabilitySerializer, 404: "Not Found"}
)
@swagger_auto_schema(
    method='PUT',
    operation_summary="Update a specific availability slot",
    request_body=DoctorAvailabilitySerializer,
    responses={200: DoctorAvailabilitySerializer, 400: "Bad Request", 404: "Not Found"}
)
@swagger_auto_schema(
    method='PATCH',
    operation_summary="Partially update a specific availability slot",
    request_body=DoctorAvailabilitySerializer,
    responses={200: DoctorAvailabilitySerializer, 400: "Bad Request", 404: "Not Found"}
)
@swagger_auto_schema(
    method='DELETE',
    operation_summary="Delete a specific availability slot",
    responses={
        200: openapi.Response(
            description="Availability slot deleted successfully.",
            examples={"application/json": {"message": "Availability slot deleted successfully."}}
        ), 404: "Not Found"
    }
)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsOwnerOrAdminForDoctor])
def retrieve_update_delete_doctor_availability_slot(request, doctor_pk, slot_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk)

    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, retrieve_update_delete_doctor_availability_slot, doctor):
        raise PermissionDenied(detail='You do not have permission to manage this doctor\'s availability.')

    availability_slot = get_object_or_404(DoctorAvailability, pk=slot_pk, doctor=doctor)

    if request.method == 'GET':
        serializer = DoctorAvailabilitySerializer(availability_slot, context={'request': request})
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = DoctorAvailabilitySerializer(availability_slot, data=request.data, partial=partial, context={'request': request})
        if serializer.is_valid():
            serializer.save() # Doctor is implicitly correct and day_of_week uniqueness handled by serializer
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        availability_slot.delete()
        return Response({"message": "Availability slot deleted successfully."}, status=status.HTTP_200_OK)

# --- DoctorUnavailability Views ---

@swagger_auto_schema(
    method='GET',
    operation_summary="List doctor's unavailability periods",
    responses={200: DoctorUnavailabilitySerializer(many=True)} # Swagger might not show pagination structure by default here
)
@api_view(['GET'])
@permission_classes([IsOwnerOrAdminForDoctor]) # Only doctor or admin can see these
def list_doctor_unavailability(request, doctor_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk)
    # Manually check object permission for the doctor
    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, list_doctor_unavailability, doctor):
        raise PermissionDenied(detail='You do not have permission to view these unavailability periods.')

    unavailability_periods = doctor.unavailable_dates.all().order_by('start_date')
    
    paginator = PageNumberPagination()
    paginator.page_size = 10 # Or another suitable default
    result_page = paginator.paginate_queryset(unavailability_periods, request)
    serializer = DoctorUnavailabilitySerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='POST',
    operation_summary="Create a new unavailability period for a doctor",
    request_body=DoctorUnavailabilitySerializer,
    responses={201: DoctorUnavailabilitySerializer}
)
@api_view(['POST'])
@permission_classes([IsOwnerOrAdminForDoctor])
def create_doctor_unavailability(request, doctor_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk)
    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, create_doctor_unavailability, doctor):
        raise PermissionDenied(detail='You do not have permission to add unavailability for this doctor.')

    serializer = DoctorUnavailabilitySerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(doctor=doctor) # Set the doctor instance
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='PUT',
    operation_summary="Update an unavailability period",
    request_body=DoctorUnavailabilitySerializer,
    responses={200: DoctorUnavailabilitySerializer}
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsOwnerOrAdminForDoctor])
def update_doctor_unavailability(request, doctor_pk, unavailability_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk)
    unavailability_period = get_object_or_404(doctor.unavailable_dates, pk=unavailability_pk)

    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, update_doctor_unavailability, doctor): # Check against doctor
        raise PermissionDenied(detail='You do not have permission to modify this unavailability period.')

    partial = request.method == 'PATCH'
    serializer = DoctorUnavailabilitySerializer(unavailability_period, data=request.data, partial=partial, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='DELETE',
    operation_summary="Delete an unavailability period",
    responses={
        200: openapi.Response(description="Unavailability period deleted successfully.", examples={"application/json": {"message": "Unavailability period deleted successfully."}}),
        404: "Not Found"
    })
@api_view(['DELETE'])
@permission_classes([IsOwnerOrAdminForDoctor])
def delete_doctor_unavailability(request, doctor_pk, unavailability_pk):
    doctor = get_object_or_404(Doctor, pk=doctor_pk)
    unavailability_period = get_object_or_404(doctor.unavailable_dates, pk=unavailability_pk)
    permission_checker = IsOwnerOrAdminForDoctor()
    if not permission_checker.has_object_permission(request, delete_doctor_unavailability, doctor): # Check against doctor
        raise PermissionDenied(detail='You do not have permission to delete this unavailability period.')
    unavailability_period.delete()
    return Response({"message": "Unavailability period deleted successfully."}, status=status.HTTP_200_OK)

swagger_auto_schema(
    method='POST',
    operation_summary="Create a new specialization",
    request_body=SpecializationSerializer,
    responses={201: SpecializationSerializer, 400: "Bad Request"}
)
@api_view(['POST'])
@permission_classes([IsAdminRole]) # Only Admin can create specializations
def create_specialization(request):
    serializer = SpecializationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='PUT',
    operation_summary="Update an existing specialization",
    request_body=SpecializationSerializer,
    responses={
        200: SpecializationSerializer,
        400: "Bad Request",
        404: "Specialization not found"
    }
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminRole]) # Only Admin can update specializations
def update_specialization(request, pk):
    specialization = get_object_or_404(Specialization, pk=pk)

    if request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = SpecializationSerializer(specialization, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='DELETE',
    operation_summary="Delete an existing specialization",
    responses={
        200: openapi.Response(
            description="Specialization deleted successfully.",
            examples={"application/json": {"message": "Specialization deleted successfully."}}
        ),
        404: "Specialization not found"
    }
)
@api_view(['DELETE'])
@permission_classes([IsAdminRole]) # Only Admin can delete specializations
def delete_specialization(request, pk):
    specialization = get_object_or_404(Specialization, pk=pk)
    specialization.delete()
    return Response({"message": "Specialization deleted successfully."}, status=status.HTTP_200_OK)

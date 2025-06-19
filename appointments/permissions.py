from rest_framework.permissions import BasePermission, SAFE_METHODS
from auth_user.models import User as AuthUserModel # Assuming your custom user model is here

class IsAdminOrReadOnly(BasePermission):
    """
    Allows full access to admin users, read-only access to others.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        return request.method in SAFE_METHODS

class IsOwnerOrDoctorOrAdmin(BasePermission):
    """
    - Patient (Owner): Can view, update (e.g., reason, notes), and cancel their own appointments.
    - Doctor: Can view appointments assigned to them, update notes, and manage status.
    - Admin: Full access.
    """
    def has_object_permission(self, request, view, obj): # obj is an Appointment instance
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin has full access
        if request.user.is_staff:
            return True

        # Patient (owner)
        if obj.patient.user == request.user and request.user.role == AuthUserModel.Role.PATIENT:
            # Patients can view, update some fields, and cancel (which is a status change)
            return True

        # Doctor assigned to the appointment
        if obj.doctor.user == request.user and request.user.role == AuthUserModel.Role.DOCTOR:
            # Doctors can view and update (e.g., notes, status)
            return True
            
        return False

class CanCreateAppointment(BasePermission):
    """
    - Authenticated Patients can create appointments for themselves.
    - Admins/Doctors can create appointments (potentially for others, handled in serializer/view).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == AuthUserModel.Role.PATIENT or \
           request.user.role == AuthUserModel.Role.DOCTOR or \
           request.user.is_staff:
            return True
        return False
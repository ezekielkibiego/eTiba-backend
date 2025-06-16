from rest_framework.permissions import BasePermission, SAFE_METHODS
from auth_user.models import User as AuthUserModel 

class IsAdminOrDoctor(BasePermission):
    """
    Allows access only to admin users or users with the doctor role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.role == AuthUserModel.Role.DOCTOR)
        )

class IsPatientUserRole(BasePermission):
    """
    Allows access only to authenticated users with the 'PATIENT' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == AuthUserModel.Role.PATIENT
        )

class IsOwnerOrAdminOrDoctorReadOnlyForPatient(BasePermission):
    """
    - Admin: All access to any patient profile.
    - Doctor: Read-only access to any patient profile.
    - Owner (Patient): Read and Update access to their own profile.
    """
    def has_object_permission(self, request, view, obj): 
        if not request.user or not request.user.is_authenticated:
            return False

        # Owner has full access to their profile
        if obj.user == request.user and request.user.role == AuthUserModel.Role.PATIENT:
            return True

        # Admin has full access
        if request.user.is_staff:
            return True

        # Doctor has read-only access
        if request.user.role == AuthUserModel.Role.DOCTOR and request.method in SAFE_METHODS:
            return True
            
        return False

    def has_permission(self, request, view): 
        if not request.user or not request.user.is_authenticated:
            return False
        return True 
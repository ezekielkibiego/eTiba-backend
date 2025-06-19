from rest_framework.permissions import BasePermission, SAFE_METHODS
from auth_user.models import User as AuthUserModel

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class IsDoctorUserRole(BasePermission):
    """
    Allows access only to authenticated users with the 'DOCTOR' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == AuthUserModel.Role.DOCTOR
        )

class IsOwnerOrAdminForDoctor(BasePermission):
    """
    - Admin: All access to any doctor profile.
    - Owner (Doctor): Read and Update access to their own profile.
    """
    def has_object_permission(self, request, view, obj): # obj is a Doctor instance
        if not request.user or not request.user.is_authenticated:
            return False

        # Owner (Doctor) has access to their profile
        if obj.user == request.user and request.user.role == AuthUserModel.Role.DOCTOR:
            return True

        # Admin has full access
        if request.user.is_staff:
            return True
        return False
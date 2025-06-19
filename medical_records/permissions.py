from rest_framework.permissions import BasePermission, SAFE_METHODS
from auth_user.models import User as AuthUserModel 

class IsDoctorUser(BasePermission):
    """
    Allows access only to users with the 'DOCTOR' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == AuthUserModel.Role.DOCTOR
        )

class IsPatientOwner(BasePermission):
    """
    Allows access only if the request.user is the patient associated with the record.
    """
    def has_object_permission(self, request, view, obj): # obj is MedicalRecord instance
        return obj.patient.user == request.user

class IsRecordCreatorOrAdmin(BasePermission):
    """
    Allows access only if the request.user is the creator of the record (doctor) or an admin.
    Assumes MedicalRecord has a 'created_by' field linked to the User.
    """
    def has_object_permission(self, request, view, obj): # obj is MedicalRecord instance
        if not request.user or not request.user.is_authenticated:
            return False
        # Check if created_by field exists and matches the request user
        return obj.created_by == request.user or request.user.is_staff

class CanViewMedicalRecord(BasePermission):
    """
    - Patient can view their own records.
    - Doctor who created the record can view it.
    - Doctor associated with the appointment (if record is linked) can view it.
    - Admin can view any record.
    """
    def has_object_permission(self, request, view, obj): # obj is MedicalRecord instance
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True
        
        if request.user.role == AuthUserModel.Role.PATIENT and obj.patient.user == request.user:
            return True
        
        if request.user.role == AuthUserModel.Role.DOCTOR:
            if obj.created_by == request.user: # Doctor who created it
                return True
            if obj.appointment and obj.appointment.doctor.user == request.user: # Doctor of the linked appointment
                return True
        
        return False
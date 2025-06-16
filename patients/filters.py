import django_filters
from .models import Patient

class PatientFilter(django_filters.FilterSet):
    # Filters for user fields (accessed via patient.user)
    first_name = django_filters.CharFilter(field_name='user__first_name', lookup_expr='icontains', label="Patient's First Name (contains, case-insensitive)")
    last_name = django_filters.CharFilter(field_name='user__last_name', lookup_expr='icontains', label="Patient's Last Name (contains, case-insensitive)")
    email = django_filters.CharFilter(field_name='user__email', lookup_expr='iexact', label="Patient's Email (exact, case-insensitive)")
    phone = django_filters.CharFilter(field_name='user__phone', lookup_expr='icontains', label="Patient's Phone Number (contains, case-insensitive)")

    # Filters for patient fields
    class Meta:
        model = Patient
        fields = {
            'gender': ['exact'],
            'date_of_birth': ['exact', 'year', 'month', 'day', 'year__gt', 'year__lt'], # Allows various date lookups
            'address': ['icontains'],
            'insurance_provider': ['icontains'],
            'insurance_number': ['iexact'], 
            'medical_history': ['icontains'],
            'allergies': ['icontains'],
            'current_medications': ['icontains'],
        }
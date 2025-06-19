import django_filters
from .models import Doctor, Specialization
from django.db.models import Q

class DoctorFilter(django_filters.FilterSet):
    specialization_name = django_filters.CharFilter(
        field_name='specializations__name',
        lookup_expr='iexact',
        label='Specialization Name (exact match, case-insensitive)'
    )
    specialization_id = django_filters.UUIDFilter(
        field_name='specializations__id',
        label='Specialization ID'
    )
    available_from = django_filters.DateFilter(
        method='filter_available_from',
        label='Available From (YYYY-MM-DD) - Checks general availability and no conflicting unavailability periods.'
    )
    phone = django_filters.CharFilter(
        field_name='user__phone',
        lookup_expr='icontains',
        label="Doctor's Phone Number (contains, case-insensitive)"
    )

    class Meta:
        model = Doctor
        fields = {
            'is_available': ['exact'],
            'office_address': ['icontains'], # Case-insensitive partial match
            'years_of_experience': ['exact', 'gte', 'lte'],
            'consultation_fee': ['exact', 'gte', 'lte'],
        }

    def filter_available_from(self, queryset, name, value):
        """
        Filters doctors who are generally available and do not have an unavailability
        period clashing with the given 'available_from' date.
        """
        # Filter for doctors who are generally available
        available_doctors_queryset = queryset.filter(is_available=True)
        
        # Exclude doctors who have an unavailability period covering the 'value' date
        # An unavailability period (start_date, end_date) clashes if:
        # unavailability.start_date <= value <= unavailability.end_date
        return available_doctors_queryset.exclude(
            unavailable_dates__start_date__lte=value,
            unavailable_dates__end_date__gte=value
        )
from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('<uuid:pk>/', views.AppointmentRetrieveUpdateDestroyView.as_view(), name='appointment-detail'),
    # DELETE on the above URL handles cancellation by updating status.
    path('<uuid:pk>/status/', views.update_appointment_status_view, name='appointment-update-status'),
    path('availability/', views.check_availability_view, name='check-availability'),
]
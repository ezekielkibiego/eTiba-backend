from django.urls import path
from . import views

urlpatterns = [
    # Specializations
    path('specializations/', views.list_specializations, name='specialization-list'),
    path('specializations/create/', views.create_specialization, name='specialization-create'),
    path('specializations/<uuid:pk>/update/', views.update_specialization, name='specialization-update'),
    path('specializations/<uuid:pk>/delete/', views.delete_specialization, name='specialization-delete'),
    
    # Doctors
    path('<uuid:pk>/', views.retrieve_doctor, name='doctor-detail'),
    path('', views.list_doctors, name='doctor-list'),
    path('register/', views.register_doctor, name='doctor-register'), # Changed from POST on /doctors/
    path('<uuid:pk>/update/', views.update_doctor, name='doctor-update'),
    path('<uuid:pk>/deactivate/', views.deactivate_doctor, name='doctor-deactivate'),
    
    # Availability
    path('<uuid:doctor_pk>/availability/', views.get_doctor_availability, name='doctor-get-availability-list'), # Renamed for clarity
    path('<uuid:doctor_pk>/availability/update/', views.update_doctor_availability, name='doctor-update-availability-bulk'), # Renamed for clarity
    path('<uuid:doctor_pk>/availability/slots/<uuid:slot_pk>/', views.retrieve_update_delete_doctor_availability_slot, name='doctor-availability-slot-detail'),
    
    # Unavailability
    path('<uuid:doctor_pk>/unavailability/', views.list_doctor_unavailability, name='doctor-list-unavailability'),
    path('<uuid:doctor_pk>/unavailability/create/', views.create_doctor_unavailability, name='doctor-create-unavailability'),
    path('<uuid:doctor_pk>/unavailability/<uuid:unavailability_pk>/update/', views.update_doctor_unavailability, name='doctor-update-unavailability'),
    path('<uuid:doctor_pk>/unavailability/<uuid:unavailability_pk>/delete/', views.delete_doctor_unavailability, name='doctor-delete-unavailability'),

]
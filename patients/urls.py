from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.list_patients, name='patient-list'),
    path('register/', views.register_patient, name='patient-register'), 
    path('me/', views.patient_me_profile, name='patient-me'),
    path('<uuid:pk>/', views.retrieve_patient, name='patient-detail'),
    path('<uuid:pk>/update/', views.update_patient, name='patient-update'), 
    path('<uuid:pk>/deactivate/', views.deactivate_patient, name='patient-deactivate'), 
]
from django.urls import path
from .views import (
    MedicalRecordListCreateView,
    MedicalRecordRetrieveUpdateDestroyView,
    MedicalRecordAttachmentUploadView,
    MedicalRecordAttachmentDetailView,
)

app_name = 'medical_records'

urlpatterns = [
    path('', MedicalRecordListCreateView.as_view(), name='medicalrecord-list-create'),
    path('<uuid:pk>/', MedicalRecordRetrieveUpdateDestroyView.as_view(), name='medicalrecord-detail'),
    path('<uuid:record_pk>/attachments/', MedicalRecordAttachmentUploadView.as_view(), name='medicalrecord-attachment-upload'),
    path('<uuid:record_pk>/attachments/<uuid:attachment_pk>/', MedicalRecordAttachmentDetailView.as_view(), name='medicalrecord-attachment-detail'),
]
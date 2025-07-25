# Generated by Django 5.2.1 on 2025-06-15 18:19

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appointments', '0001_initial'),
        ('doctors', '0001_initial'),
        ('patients', '0002_alter_patient_gender'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalRecord',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('record_type', models.CharField(choices=[('consultation', 'Consultation Notes'), ('diagnosis', 'Diagnosis'), ('prescription', 'Prescription'), ('lab_result', 'Lab Result'), ('imaging', 'Imaging Result'), ('procedure', 'Procedure Notes'), ('discharge', 'Discharge Summary'), ('referral', 'Referral')], max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('summary', models.TextField(blank=True, help_text='Brief summary of the record', null=True)),
                ('diagnosis', models.TextField(blank=True, null=True)),
                ('treatment_plan', models.TextField(blank=True, help_text='Proposed treatment plan', null=True)),
                ('medications', models.JSONField(blank=True, help_text='List of prescribed medications and dosages', null=True)),
                ('allergies', models.JSONField(blank=True, help_text='Known allergies and reactions', null=True)),
                ('lab_results', models.JSONField(blank=True, help_text='Structured lab results data', null=True)),
                ('vital_signs', models.JSONField(blank=True, help_text='Blood pressure, temperature, etc.', null=True)),
                ('is_confidential', models.BooleanField(default=False, help_text='Highly sensitive information')),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medical_records', to='appointments.appointment')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('doctor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_medical_records', to='doctors.doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medical_records', to='patients.patient')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'medical_records',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MedicalRecordAccess',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('access_type', models.CharField(choices=[('view', 'View'), ('edit', 'Edit'), ('delete', 'Delete'), ('download', 'Download')], max_length=20)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('accessed_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medical_record_accesses', to=settings.AUTH_USER_MODEL)),
                ('medical_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_logs', to='medical_records.medicalrecord')),
            ],
            options={
                'db_table': 'medical_record_access',
            },
        ),
        migrations.CreateModel(
            name='MedicalRecordAttachment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to='medical_records/%Y/%m/%d/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])])),
                ('filename', models.CharField(max_length=255)),
                ('file_size', models.PositiveIntegerField(help_text='File size in bytes')),
                ('content_type', models.CharField(max_length=100)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('medical_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='medical_records.medicalrecord')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'medical_record_attachments',
            },
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['patient', 'created_at'], name='medical_rec_patient_bfaf9b_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['doctor', 'created_at'], name='medical_rec_doctor__53e85b_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['record_type'], name='medical_rec_record__6b7b73_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecord',
            index=models.Index(fields=['appointment'], name='medical_rec_appoint_c6c058_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecordaccess',
            index=models.Index(fields=['medical_record', 'created_at'], name='medical_rec_medical_5561b5_idx'),
        ),
        migrations.AddIndex(
            model_name='medicalrecordaccess',
            index=models.Index(fields=['accessed_by', 'created_at'], name='medical_rec_accesse_ba0dd2_idx'),
        ),
    ]

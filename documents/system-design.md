# Etiba - Clinic Management System
## System Design Document

- **Version:** 1.0
- **Date:** June 15, 2025
- **Author(s):** kibiezekiel@gmail.com

---

## 1. Introduction

### 1.1. Purpose
- This document outlines the system design for Etiba, a comprehensive clinic management system. 
- It details the architecture, modules, data models, API design, and key functionalities of the application.

### 1.2. Project Overview
- Etiba aims to streamline healthcare operations by providing a digital platform for managing patients, doctors, appointments, medical records, and notifications. 
- It is built using Python, Django, Django REST Framework, Celery, Redis, and PostgreSQL.

### 1.3. Goals and Objectives
*   Provide secure and role-based access for administrators, doctors, and patients.
*   Enable efficient management of patient and doctor profiles.
*   Facilitate appointment scheduling and management.
*   Offer a secure system for creating, storing, and accessing medical records.
*   Implement an in-app notification system for important events.
*   Deliver a well-documented RESTful API for potential integrations and frontend consumption.

### 1.4. Scope
**In Scope:**
*   User Authentication and Authorization (Registration, Login, Email Verification, JWT, Role-based access).
*   Patient Profile Management (CRUD, Admin/Doctor registration).
*   Doctor Profile Management (CRUD, Specializations, Availability, Unavailability).
*   Appointment Management (Booking, Status Updates).
*   Medical Records Management (CRUD, File Attachments, Access Control, Audit).
*   In-app Notification System (Asynchronous via Celery).
*   Admin Interface for system management.
*   API Documentation (Swagger/ReDoc).

**Out of Scope (for current version, unless specified otherwise):**
*   Billing and Payments.
*   Telemedicine/Video Consultation features.
*   Pharmacy/Inventory Management.
*   Advanced reporting and analytics beyond basic listings.

---

## 2. System Architecture

### 2.1. Architectural Style
Etiba follows a **Monolithic Architecture** based on the Django framework. It employs a 3-tier architecture:
*   **Presentation Tier:** RESTful API endpoints serving JSON data (consumed by potential frontends or third-party services). API documentation via Swagger/ReDoc.
*   **Application Tier (Business Logic):** Django apps handling business rules, data processing, and service logic. Celery for asynchronous task processing.
*   **Data Tier:** PostgreSQL database for persistent storage. Redis for caching and Celery message broking.

### 2.2. Technology Stack
*   **Backend Framework:** Django, Django REST Framework
*   **Programming Language:** Python
*   **Database:** PostgreSQL
*   **Task Queue:** Celery
*   **Message Broker/Cache:** Redis
*   **Authentication:** JWT (Simple JWT)
*   **API Documentation:** drf-yasg (Swagger/ReDoc)
*   **Development Environment:** Virtual Environment, Git

### 2.3. Key Modules (Django Apps)
*   **`auth_user`:** Manages user accounts, authentication, JWT, email verification, and roles.
*   **`patients`:** Manages patient profiles, including personal, contact, insurance, and basic medical information.
*   **`doctors`:** Manages doctor profiles, specializations, consultation fees, availability schedules, and unavailability periods.
*   **`appointments`:** Handles the creation, scheduling, and status management of appointments.
*   **`medical_records`:** Manages patient medical records, including different record types, file attachments, and access logs.
*   **`notifications`:** Provides an in-app notification system, with notifications generated asynchronously.

---

## 3. Data Model / Database Design

### 3.1. Database
PostgreSQL is the chosen relational database management system (RDBMS) due to its robustness, scalability, and rich feature set.

### 3.2. Key Entities and Relationships


*   **User (`auth_user.User`):**
    *   Core model for all system users (Admin, Doctor, Patient).
    *   Fields: `email` (username), `password`, `first_name`, `last_name`, `phone`, `role`, `is_active`, `is_staff`, etc.
    *   One-to-One with `Patient` (if role is Patient).
    *   One-to-One with `Doctor` (if role is Doctor).

*   **Patient (`patients.Patient`):**
    *   One-to-One with `User`.
    *   Fields: `date_of_birth`, `gender`, `address`, `emergency_contact`, `insurance_provider`, `insurance_number`, `medical_history`, `allergies`, `current_medications`.
    *   Many-to-Many with `MedicalRecord` (a patient has many medical records).

*   **Specialization (`doctors.Specialization`):**
    *   Fields: `name`, `description`.
    *   Many-to-Many with `Doctor` (through `DoctorSpecialization`).

*   **Doctor (`doctors.Doctor`):**
    *   One-to-One with `User`.
    *   Fields: `license_number`, `years_of_experience`, `consultation_fee`, `bio`, `office_address`, `is_available`.
    *   Many-to-Many with `Specialization` (through `DoctorSpecialization`).
    *   One-to-Many with `DoctorAvailability`.
    *   One-to-Many with `DoctorUnavailability`.
    *   Many-to-Many with `MedicalRecord` (a doctor creates/is associated with many medical records).

*   **DoctorSpecialization (`doctors.DoctorSpecialization`):**
    *   Through model for `Doctor` and `Specialization`.
    *   Fields: `doctor`, `specialization`, `board_certified`, `certification_date`.

*   **DoctorAvailability (`doctors.DoctorAvailability`):**
    *   Many-to-One with `Doctor`.
    *   Fields: `day_of_week`, `start_time`, `end_time`, `break_start`, `break_end`, `is_active`.

*   **DoctorUnavailability (`doctors.DoctorUnavailability`):**
    *   Many-to-One with `Doctor`.
    *   Fields: `start_date`, `end_date`, `reason`.

*   **Appointment (`appointments.Appointment`):**
    *   Many-to-One with `Patient`.
    *   Many-to-One with `Doctor`.
    *   Fields: `appointment_datetime`, `reason`, `status`, `duration`, `notes`, etc.
    *   One-to-Many with `AppointmentStatusHistory`.
    *   One-to-One (optional) with `MedicalRecord`.

*   **MedicalRecord (`medical_records.MedicalRecord`):**
    *   Many-to-One with `Patient`.
    *   Many-to-One with `Doctor` (creator/associated doctor).
    *   One-to-One (optional) with `Appointment`.
    *   Fields: `record_type`, `title`, `summary`, `diagnosis`, `treatment_plan`, `medications`, `allergies`, `lab_results`, `vital_signs`, `is_confidential`.
    *   Inherits `created_by`, `updated_by`, `created_at`, `updated_at` (from `AuditModel`).
    *   Inherits `is_deleted`, `deleted_at` (from `SoftDeleteModel`).
    *   One-to-Many with `MedicalRecordAttachment`.

*   **MedicalRecordAttachment (`medical_records.MedicalRecordAttachment`):**
    *   Many-to-One with `MedicalRecord`.
    *   Fields: `file`, `filename`, `file_size`, `content_type`, `description`, `uploaded_by`, `uploaded_at`.

*   **MedicalRecordAccess (`medical_records.MedicalRecordAccess`):**
    *   Many-to-One with `MedicalRecord`.
    *   Many-to-One with `User` (accessed_by).
    *   Fields: `access_type`, `ip_address`, `user_agent`.
    *   Inherits `created_at` (timestamp of access).

*   **Notification (`notifications.Notification`):**
    *   Many-to-One with `User` (recipient).
    *   Generic Foreign Keys for `actor`, `target`, `action_object`.
    *   Fields: `verb`, `description`, `read`, `timestamp`.

---

## 4. API Design

### 4.1. Principles
*   RESTful architecture.
*   Stateless communication.
*   JSON for request and response payloads.
*   Standard HTTP methods (GET, POST, PUT, PATCH, DELETE).
*   Consistent URL naming conventions.
*   Clear and informative error responses.

### 4.2. Authentication
*   JWT (JSON Web Tokens) using `djangorestframework-simplejwt`.
*   Access tokens for authorizing requests.
*   Refresh tokens for obtaining new access tokens.
*   Endpoints: `/api/auth/login/`, `/api/auth/token/refresh/`, `/api/auth/logout/`.

### 4.3. API Endpoints Summary
*(Refer to `urls.py` of each app for detailed paths. This is a high-level summary.)*

*   **Auth User (`/api/auth/`):**
    *   `POST /register/`: User registration.
    *   `POST /login/`: User login (token obtain).
    *   `GET /verify-email/<uidb64>/<token>/`: Email verification.
    *   `POST /resend-verification-email/`: Resend verification email.
    *   `POST /logout/`: User logout.
*   **Patients (`/api/patients/`):**
    *   `GET /`: List patients (Admin/Doctor, paginated, filtered, searched).
    *   `POST /register/`: Register a new patient (Admin/Doctor).
    *   `GET /me/`: Get current authenticated patient's profile.
    *   `PUT, PATCH /me/`: Update current authenticated patient's profile.
    *   `GET /<uuid:pk>/`: Retrieve specific patient profile.
    *   `PUT, PATCH /<uuid:pk>/update/`: Update specific patient profile (Admin/Owner).
    *   `DELETE /<uuid:pk>/deactivate/`: Deactivate patient account (Admin).
*   **Doctors (`/api/doctors/`):**
    *   `GET /`: List doctors (Authenticated users, paginated, filtered, searched).
    *   `POST /register/`: Register a new doctor (Admin).
    *   `GET /<uuid:pk>/`: Retrieve specific doctor profile.
    *   `PUT, PATCH /<uuid:pk>/update/`: Update specific doctor profile (Admin/Owner).
    *   `DELETE /<uuid:pk>/deactivate/`: Deactivate doctor account (Admin).
    *   `GET /specializations/`: List specializations.
    *   `POST /specializations/create/`: Create specialization (Admin).
    *   `PUT, PATCH /specializations/<uuid:pk>/update/`: Update specialization (Admin).
    *   `DELETE /specializations/<uuid:pk>/delete/`: Delete specialization (Admin).
    *   Availability endpoints: `GET, PUT /<uuid:doctor_pk>/availability/`, `GET, PUT, PATCH, DELETE /<uuid:doctor_pk>/availability/slots/<uuid:slot_pk>/`.
    *   Unavailability endpoints: `GET, POST /<uuid:doctor_pk>/unavailability/`, `PUT, PATCH, DELETE /<uuid:doctor_pk>/unavailability/<uuid:unavailability_pk>/`.
*   **Appointments (`/api/appointments/`):**
    *   `GET, POST /`: List and create appointments.
    *   `GET, PUT, PATCH, DELETE /<uuid:pk>/`: Retrieve, update, delete specific appointment.
    *   `POST /<uuid:pk>/status/`: Update appointment status.
    *   `GET /availability/`: Check doctor availability.
*   **Medical Records (`/api/medical-records/`):**
    *   `GET, POST /`: List and create medical records.
    *   `GET, PUT, PATCH, DELETE /<uuid:pk>/`: Retrieve, update, (soft) delete specific medical record.
    *   `POST /<uuid:record_pk>/attachments/`: Upload attachment to a medical record.
    *   `DELETE /<uuid:record_pk>/attachments/<uuid:attachment_pk>/`: Delete an attachment.
*   **Notifications (`/api/notifications/`):**
    *   `GET /`: List notifications for the authenticated user.
    *   `PATCH /<uuid:pk>/status/`: Update notification read status.

### 4.4. API Documentation
*   Generated using `drf-yasg`.
*   Accessible via `/api/swagger/` (Swagger UI) and `/api/redoc/` (ReDoc).

---

## 5. User Roles and Permissions

### 5.1. Roles
*   **Patient:** Can manage their own profile, book appointments, view their medical records and notifications.
*   **Doctor:** Can manage their profile and availability, view patient profiles, create and manage medical records for their patients, manage appointments.
*   **Administrator (Admin/Staff):** Has superuser privileges, can manage all aspects of the system including users, doctors, patients, specializations, and system settings.

### 5.2. Permissions System
*   Django REST Framework's permission classes are used.
*   Custom permission classes are defined in each app's `permissions.py` (e.g., `IsAdminOrDoctor`, `IsOwnerOrAdminForDoctor`, `CanViewMedicalRecord`).
*   Permissions are applied at the view level and, where necessary, at the object level.

---

## 6. Key Features Deep Dive

### 6.1. `auth_user` Module
*   **User Registration:** `UserRegistrationSerializer` handles creation. Passwords are validated and hashed. Users are initially inactive.
*   **Email Verification:** `send_verification_email_task` (Celery task) sends an email with a unique token. `verify_email_view` activates the user. `AccountActivationTokenGenerator` generates tokens.
*   **Login:** `CustomTokenObtainPairView` and `CustomTokenObtainPairSerializer` handle login, returning JWTs and user data. Prevents login for inactive accounts.
*   **Logout:** `user_logout_view` blacklists the refresh token.
*   **Resend Verification:** `resend_verification_email_view` allows users to request a new verification email.

### 6.2. `patients` Module
*   **Profile Management:** `PatientProfileSerializer` for viewing and updating. `PatientUserSerializer` for nested user details.
*   **Admin/Doctor Registration:** `PatientRegistrationSerializer` allows Admins/Doctors to create patient accounts. An email verification is sent to the patient.
*   **`/me` Endpoint:** `patient_me_profile` view for authenticated patients to manage their own data.
*   **Listing & Filtering:** `list_patients` view uses `PatientFilter` and `SearchFilter` for advanced querying by Admins/Doctors. Pagination is implemented.
*   **Permissions:** `IsAdminOrDoctor`, `IsPatientUserRole`, `IsOwnerOrAdminOrDoctorReadOnlyForPatient` control access.

### 6.3. `doctors` Module
*   **Profile Management:** `DoctorProfileSerializer` for viewing and updating. `DoctorUserSerializer` for nested user details. `specialization_ids` for managing specializations on update.
*   **Admin Registration:** `DoctorRegistrationSerializer` allows Admins to create doctor accounts. Email verification is sent.
*   **Specializations:** CRUD operations for `Specialization` model via dedicated views, restricted to Admins.
*   **Availability:** `DoctorAvailabilitySerializer` and dedicated views (`get_doctor_availability`, `update_doctor_availability`, `retrieve_update_delete_doctor_availability_slot`) manage weekly schedules.
*   **Unavailability:** `DoctorUnavailabilitySerializer` and dedicated views manage specific off-dates.
*   **Listing & Filtering:** `list_doctors` view uses `DoctorFilter` and `SearchFilter`.
*   **Permissions:** `IsAdminUser` (for `Specialization`), `IsOwnerOrAdminForDoctor` control access.

### 6.4. `appointments` Module
*   **Booking & Management:** `AppointmentListCreateView` and `AppointmentRetrieveUpdateDestroyView` for CRUD.
*   **Status Updates:** `update_appointment_status_view` for changing appointment status, logs history.
*   **Availability Check:** `check_availability_view` for finding available slots.
*   **Permissions:** `CanCreateAppointment`, `CanViewAppointmentDetails`, `CanUpdateAppointmentStatus`, `CanUpdateAppointment`, `CanDeleteAppointment`.
*   **Notifications:** `create_appointment_creation_notification_task` and `create_appointment_change_notification_task` (Celery tasks) are triggered on appointment creation and status changes.

### 6.5. `medical_records` Module
*   **CRUD Operations:** `MedicalRecordListCreateView` and `MedicalRecordRetrieveUpdateDestroyView`. Soft delete is implemented.
*   **Serializers:** `MedicalRecordSerializer` (includes nested patient/doctor details and attachments), `MedicalRecordAttachmentSerializer`.
*   **Attachments:** `MedicalRecordAttachmentUploadView` (form-data for file upload) and `MedicalRecordAttachmentDetailView`.
*   **Permissions:** `IsDoctorUser` (for creation), `IsRecordCreatorOrAdmin` (for update/delete), `CanViewMedicalRecord` (for retrieval).
*   **Audit:** `MedicalRecordAccess` model exists for logging access (implementation of logging in views is a next step).
*   **Data Integrity:** `AuditModel` and `SoftDeleteModel` are inherited by `MedicalRecord`.

### 6.6. `notifications` Module
*   **In-app Notifications:** `Notification` model stores notification data.
*   **API:** `list_notifications` and `update_notification_status` views.
*   **Asynchronous Creation:** Celery tasks (e.g., `create_appointment_creation_notification_task`) are used to generate notifications without blocking the main request-response cycle.

---

## 7. Asynchronous Processing (Celery & Redis)

*   **Celery:** Used for offloading long-running or non-critical tasks from the main request-response cycle.
    *   Sending email verifications (`auth_user.tasks.send_verification_email_task`).
    *   Creating notifications (`notifications.tasks.*`).
*   **Redis:** Serves as the message broker for Celery, queuing tasks for workers. Can also be used for caching if needed in the future.
*   **Worker Setup:** Requires a separate Celery worker process to be running.
*   **Beat Setup:** Requires a Celery Beat process if scheduled/periodic tasks are implemented (e.g., using `django-celery-beat`).

---

## 8. Scalability and Performance Considerations

*   **Database Query Optimization:**
    *   Use of `select_related` and `prefetch_related` in views to minimize database queries (e.g., in `MedicalRecordListCreateView`, `Doctor.list_doctors`).
*   **Pagination:** Implemented for list views (`PageNumberPagination`, `StandardResultsSetPagination`) to handle large datasets efficiently.
*   **Asynchronous Tasks:** Celery offloads tasks like email sending and notification creation.
*   **Indexing:** Database indexes are defined on models for frequently queried fields to improve query performance.
*   **Caching:** Redis can be leveraged for caching frequently accessed, non-volatile data (not explicitly implemented yet but Redis is in the stack).

---

## 9. Security Considerations

*   **Authentication:** Robust JWT-based authentication.
*   **Authorization:** Granular role-based and object-level permissions.
*   **Password Management:** Passwords are hashed using Django's default password hashers. `validate_password` is used.
*   **Email Verification:** Prevents registration with unverified email addresses and ensures users own the email.
*   **Input Validation:** Serializers perform data validation before processing.
*   **CSRF Protection:** Django's built-in CSRF protection is active for session-based parts (like Django Admin), though DRF APIs are typically stateless.
*   **HTTPS:** Recommended for production deployment to encrypt data in transit.
*   **Sensitive Data:** Medical records marked `is_confidential` can have stricter access rules (current permissions provide a base). `MedicalRecordAccess` logs provide an audit trail.
*   **Dependency Management:** Keeping libraries up-to-date to patch vulnerabilities.
*   **Environment Variables:** Sensitive configurations (secret key, database credentials, email passwords) are managed via environment variables (e.g., `.env` file).

---

## 10. Deployment Considerations

*   **WSGI/ASGI Server:** A production-grade server like Gunicorn (for WSGI) or Uvicorn/Daphne (for ASGI if Channels are used) is required instead of the Django development server.
*   **Static & Media Files:** Configuration for serving static files (CSS, JS, images) and user-uploaded media files (e.g., using Nginx or a cloud storage service like S3).
*   **Database:** Production PostgreSQL instance.
*   **Redis:** Production Redis instance.
*   **Celery Workers & Beat:** Processes need to be managed (e.g., using Supervisor, systemd).
*   **Environment Configuration:** Managing different settings for development, staging, and production.
*   **Logging & Monitoring:** Setting up comprehensive logging and monitoring tools.
*   **Backups:** Regular database and file storage backups.

---

## 11. Future Enhancements (Potential)
*   Advanced search and filtering capabilities across more modules.
*   Implementation of a calendar view for appointments.
*   Bulk operations for administrators.
*   Basic reporting endpoints.
*   Full implementation of `MedicalRecordAccess` logging in views.
*   Integration with payment gateways.
*   Real-time features (e.g., chat, live appointment status updates using Django Channels).
*   Two-Factor Authentication (2FA).
*   More detailed audit trails for critical actions.
*   Internationalization (i18n) and Localization (l10n).

---

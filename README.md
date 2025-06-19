# Etiba 

- Etiba is a robust and feature-rich clinic management system designed to streamline healthcare operations. 
- Built with Python, Django, and Django REST Framework, it provides a comprehensive suite of tools for managing patients, doctors, appointments, medical records, and notifications.

## **Built with**
<p align='center'>
  <a href="https://www.python.org/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=python" alt="Python"/></a>
  <a href="https://www.djangoproject.com/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=django" alt="Django"/></a>
  <a href="https://redis.io/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=redis" alt="Redis"/></a>
  <a href="https://www.postgresql.org/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=postgres" alt="PostgreSQL"/></a>
  <a href="https://git-scm.com/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=git" alt="Git"/></a>
  <a href="https://github.com/" target="_blank" rel="noreferrer"><img src="https://skillicons.dev/icons?i=github" alt="GitHub"/></a>
</p>

## Features

*   **User Authentication & Authorization:**
    *   Secure user registration (Patient, Doctor, Admin roles).
    *   Email verification for new accounts (asynchronous via Celery).
    *   JWT-based authentication (Access & Refresh tokens).
    *   Password reset functionality (implied, standard for auth systems).
    *   Role-based access control for different system functionalities.
    *   Secure logout mechanism.
*   **Patient Management:**
    *   Detailed patient profiles (personal info, medical history, insurance).
    *   Patient registration by Admins/Doctors.
    *   Patients can view and update their own profiles (`/me` endpoint).
    *   Admin/Doctor views for patient listings with advanced search and filtering.
    *   Patient account deactivation.
*   **Doctor Management:**
    *   Comprehensive doctor profiles (license, specializations, experience, fees, bio).
    *   Management of medical specializations.
    *   Doctor availability scheduling (weekly recurring slots).
    *   Management of doctor unavailability periods (vacations, etc.).
    *   Admin registration for new doctors.
    *   Doctors can update their own profiles.
    *   Public listing of doctors with search and filtering capabilities.
*   **Appointment Management:**
    *   Appointment booking functionality.
    *   Appointment status updates.
    *   (Further details to be expanded based on `appointments` app implementation).
*   **Medical Records:**
    *   Secure creation and management of patient medical records.
    *   Support for various record types (consultation notes, lab results, prescriptions, etc.).
    *   File attachments for medical documents (e.g., PDFs, images).
    *   Detailed access controls:
        *   Patients can view their own records.
        *   Doctors can create records and view records they created or are associated with.
        *   Admins have full access.
    *   Soft deletion for medical records.
    *   Audit trail for medical record access (`MedicalRecordAccess` model).
*   **Notifications:**
    *   In-app notifications.
    *   Asynchronous notification creation (e.g., upon new appointment booking) using Celery.
*   **API & Documentation:**
    *   Well-structured RESTful API.
    *   Automated API documentation using Swagger (drf-yasg).
*   **Admin Interface:**
    *   Comprehensive Django Admin panel for managing all core entities.

## Tech Stack

*   **Backend:**
    *   [Python](https://www.python.org/) 
    *   [Django](https://www.djangoproject.com/) & Django REST Framework
*   **Task Queue:**
    *   [Celery](https://docs.celeryq.dev/) 
*   **Message Broker/Cache:**
    *   [Redis](https://redis.io/) 
*   **Database:**
    *   [PostgreSQL](https://www.postgresql.org/)  
*   **API Documentation:**
    *   drf-yasg (for Swagger UI / ReDoc)
*   **Development Environment:**
    *   [VSCode](https://code.visualstudio.com/) 

## Getting Started

### Prerequisites

*   Python (3.10+ recommended)
*   Poetry (or pip) for dependency management
*   PostgreSQL (or other preferred database)
*   Redis server (for Celery)
*   Mail server (e.g., SMTP for development like MailHog, or a production email service)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/etiba-backend.git
    cd etiba
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    *   Create a `.env` file in the project root (where `manage.py` is).
    *   Copy the contents of [`.env.sample`](.env.sample) to your new `.env` file:
        ```bash
        cp .env.sample .env
        ```
    *   Open the `.env` file and fill in the required values for your environment (e.g., database credentials, email settings, secret key). Refer to the comments in `.env.sample` for guidance on each variable.

5.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

6.  **Create a superuser (for admin access):**
    ```bash
    python manage.py createsuperuser
    ```

### Running the Application

1.  **Start the Django development server:**
    ```bash
    python manage.py runserver
    ```
    The application will typically be available at `http://127.0.0.1:8000/`.

2.  **Start the Celery worker (in a separate terminal):**
    ```bash
    celery -A etiba worker -l info
    ```
    *(Replace `etiba` with your Django project name if different)*

3.  **Start Celery Beat (currently not implemented for future use ):**
    ```bash
    celery -A etiba beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ```
## System Architecture
The system Architecture can be found in the [document](./documents/system-design.md) which explains more the decisions on the project.

## Project Structure

The project is organized into several Django apps:

*   `auth_user`: Handles user authentication, registration, and JWT management.
*   `patients`: Manages patient profiles and related data.
*   `doctors`: Manages doctor profiles, specializations, and availability.
*   `appointments`: Handles appointment scheduling and management.
*   `notifications`: Manages in-app notifications, often triggered by events like new appointments.
*   `medical_records`: Manages patient medical records, including attachments and access logs.

## API Documentation

API documentation is available via Swagger UI and ReDoc, generated by `drf-yasg`.
Once the server is running, you can typically access them at:

*   **Swagger UI:** `{{BASE_URL}}/api/swagger/`
*   **ReDoc:** `{{BASE_URL}}/api/redoc/`

## Testing

The project can be tested in multiple ways:

1.  **API Endpoint Testing (Manual):**
    *   Use a tool like Postman or Insomnia to manually test the API endpoints.
    *   Ensure you handle authentication (obtain JWT tokens) and test various request types (GET, POST, PUT, DELETE) with appropriate payloads and headers.
    *   Verify response codes, data accuracy, and error handling.
    * the postman collection used is [here](./postman/collections/43112290-95b65dd7-b3b1-4538-86c9-7ee1eb5e2f25.json). 
    - *(the postman collection is linked via github. Contact me if you want to be write access.)*

2.  **Automated Unit & Integration Tests:**
    *   Run Django's built-in test runner for automated tests (unit tests, integration tests):
        ```bash
        python manage.py test
        ```
    *   To run tests for a specific app:
        ```bash
        python manage.py test your_app_name
        ```
    *   (Ensure test files like `tests.py` are populated within each app for comprehensive coverage).

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature-name`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add some feature'`).
5. Push to the branch (`git push origin feature/your-feature-name`).
6. Open a Pull Request.

Please ensure your code adheres to the project's coding standards and includes tests for new features.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details 

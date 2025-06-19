import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from cloudinary.models import CloudinaryField 
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        """Creates and saves a regular User with a given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Creates and saves a superuser with a given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN) 

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the primary identifier.
    Features roles and Cloudinary integration for profile pictures.
    """
    class Role(models.TextChoices):
        # Defines user roles for the application.
        ADMIN = 'ADMIN', _('Admin')
        PATIENT = 'PATIENT', _('Patient')
        DOCTOR = 'DOCTOR', _('Doctor')

    # --- Fields ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150) 
    last_name = models.CharField(_('last name'), max_length=150)  
    phone = models.CharField(_('phone number'), max_length=20, blank=True, null=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.PATIENT)
    profile_picture = CloudinaryField('profile_picture', folder='profile_pics', null=True, blank=True)

    # --- Django's required fields ---
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False) # Default to False for email verification workflows.
    date_joined = models.DateTimeField(auto_now_add=True)

    # --- Relationships with explicit related_name to avoid clashes ---
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="auth_user_groups",  # Custom related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="auth_user_permissions",  # Custom related_name
        related_query_name="user",
    )

    # --- Configuration ---
    objects = UserManager()
    
    username = None # Disable the default username field.
    USERNAME_FIELD = 'email' # Use email for authentication.
    REQUIRED_FIELDS = ['first_name', 'last_name'] # Required for 'createsuperuser' command.

    def __str__(self):
        """Returns the user's email for string representation."""
        return self.email

    def get_full_name(self):
        """Returns the user's first and last name."""
        return f"{self.first_name} {self.last_name}".strip()

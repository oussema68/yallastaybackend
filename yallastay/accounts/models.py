from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from core.models import Area, University


class UserManager(BaseUserManager):
    """Manager for User model with email as identifier (no username)."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user with email as username."""

    email = models.EmailField(unique=True)
    username = None  # Remove username, use email

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password for createsuperuser

    objects = UserManager()

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("tenant", "Tenant"),  # default renter at signup
        ("student", "Student"),  # set when university email is verified (admin flow)
        ("landlord", "Landlord"),
        ("realtor", "Realtor"),
    ]
    SEX_CHOICES = [
        ("", "Not specified"),
        ("female", "Female"),
        ("male", "Male"),
        ("prefer_not_to_say", "Prefer not to say"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
    work_area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True
    )
    bio = models.TextField(blank=True)
    # Optional renter fields (tenant / student) - improves roommate & discovery search
    place_of_work_or_studies = models.CharField(
        max_length=300,
        blank=True,
        help_text="Employer, university, or school name (optional).",
    )
    sex = models.CharField(
        max_length=20,
        blank=True,
        choices=SEX_CHOICES,
        default="",
    )
    age = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Self-reported age for search filters (optional).",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    can_manage_lifestyle = models.BooleanField(
        default=False,
        help_text="If true, user can access the lifestyle team dashboard (Services page) without Django staff.",
    )
    can_verify_documents = models.BooleanField(
        default=False,
        help_text="If true, user may use the verification staff API and console to review broker and owner documents.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} ({self.role})"


class LandlordProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="landlord_profile"
    )
    company_name = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    bank_details = models.TextField(blank=True)
    needs_assisted_listing = models.BooleanField(default=False)
    # Staff approves owner accounts in Django Admin (same pattern as RealtorProfile.is_approved).
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    # UAE: non-Emirati owners must submit residence visa + passport; Emirati may omit visa.
    is_emirati = models.BooleanField(
        null=True,
        blank=True,
        help_text="If False, a residence visa is required for verification (in addition to passport).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Landlord: {self.user.email}"


class RealtorProfile(models.Model):
    BROKERAGE_TYPE_CHOICES = [
        ("private", "Private broker"),
        ("agency", "Agency / brokerage"),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="realtor_profile"
    )
    agency_name = models.CharField(max_length=200)
    brokerage_type = models.CharField(
        max_length=20,
        choices=BROKERAGE_TYPE_CHOICES,
        default="agency",
        help_text="Private brokers are shown first to owners (less paperwork) when selecting a realtor.",
    )
    license_number = models.CharField(max_length=100, blank=True)
    rera_number = models.CharField(max_length=100, blank=True)
    orn = models.CharField(
        max_length=64,
        blank=True,
        help_text="Office Registration Number (RERA), if applicable.",
    )
    license_document = models.FileField(
        upload_to="realtor_licenses/", blank=True, null=True
    )
    bank_details = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Realtor: {self.agency_name} ({self.user.email})"


class UAEIDVerification(models.Model):
    """Emirates ID verification for students/workers. Required for viewings, reservations."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="uae_id_verification"
    )
    id_hash = models.CharField(
        max_length=128, help_text="SHA256 hash of Emirates ID number"
    )
    document = models.FileField(upload_to="verification/uae_id/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "UAE ID Verification"
        verbose_name_plural = "UAE ID Verifications"

    def __str__(self):
        return f"{self.user.email} UAE ID - {self.status}"


class UniversityVerification(models.Model):
    """University email verification for students."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="university_verification"
    )
    email = models.EmailField(help_text="University email used for verification")
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University Verification"
        verbose_name_plural = "University Verifications"

    def __str__(self):
        return f"{self.user.email} - {self.university.name} - {self.status}"

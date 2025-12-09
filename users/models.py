import os
import random
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError(_("The given email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    email_verified = models.BooleanField(_("email verified"), default=False)
    email_verification_code = models.CharField(
        _("email verification code"), max_length=6, blank=True, null=True
    )
    email_verification_code_created_at = models.DateTimeField(
        _("verification code created at"), blank=True, null=True
    )

    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def generate_verification_code(self):
        """Generate 6-digit verification code"""
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        self.email_verification_code = code
        self.email_verification_code_created_at = timezone.now()
        self.save(
            update_fields=[
                "email_verification_code",
                "email_verification_code_created_at",
            ]
        )
        return code

    def is_verification_code_valid(self, code):
        """Check validity of verification code (15 minutes)"""
        if (
            self.email_verification_code == code
            and self.email_verification_code_created_at
        ):
            expiration_time = (
                self.email_verification_code_created_at + timezone.timedelta(minutes=15)
            )
            return timezone.now() <= expiration_time
        return False

    def verify_email_with_code(self, code):
        """Verify email with code"""
        if self.is_verification_code_valid(code):
            self.email_verified = True
            self.email_verification_code = None
            self.email_verification_code_created_at = None
            self.save(
                update_fields=[
                    "email_verified",
                    "email_verification_code",
                    "email_verification_code_created_at",
                ]
            )
            return True
        return False

    def __str__(self):
        return self.email


def validate_image_extension(value):
    """Validator for checking image extension"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    if ext == ".tiff" or ext == ".tif":
        raise ValidationError(
            _("TIFF format is not supported. Use JPG, PNG, GIF or WebP.")
        )
    if ext not in valid_extensions:
        raise ValidationError(
            _("Unsupported file format. Use JPG, PNG, GIF or WebP.")
        )


def validate_image_size(value):
    """Validator for checking image size"""
    max_size = 5 * 1024 * 1024  # 5MB
    if value.size > max_size:
        raise ValidationError(
            _("File size must not exceed 5MB. Current size: %(size)sKB") % 
            {"size": value.size // 1024}
        )


class City(models.Model):
    """Model for storing list of cities"""

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("City name"),
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z\s\-]+$",
                message=_("City must contain only Latin letters, spaces and hyphens"),
            )
        ],
    )
    region = models.CharField(max_length=150, blank=True, verbose_name=_("Region"))
    country = models.CharField(max_length=100, default=_("Russia"), verbose_name=_("Country"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}" + (f" ({self.region})" if self.region else "")


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )

    avatar = models.ImageField(
        upload_to="profile_images/%Y/%m/%d/",
        blank=True,
        null=True,
        validators=[validate_image_extension, validate_image_size],
        verbose_name=_("Profile avatar"),
        help_text=_("Supported formats: JPG, PNG, GIF, WebP. Maximum size: 5MB."),
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name=_("About me"),
        help_text=_("Maximum 500 characters"),
    )

    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("City"),
        help_text=_("Select city from list"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
        ordering = ["-created_at"]

    def __str__(self):
        return _("Profile of %(email)s") % {"email": self.user.email}

    def get_avatar_url(self):
        """Return avatar URL or None if avatar not set"""
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return None

    def clean(self):
        """Additional model-level validation"""
        super().clean()

    def save(self, *args, **kwargs):
        """Override save to call clean"""
        self.full_clean()
        super().save(*args, **kwargs)
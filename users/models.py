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
            raise ValueError("The given email must be set")
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
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

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
        """Генерирует 6-значный код подтверждения"""
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
        """Проверяет валидность кода подтверждения (15 минут)"""
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
        """Подтверждает email по коду"""
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
    """Валидатор для проверки расширения изображения"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    if ext == ".tiff" or ext == ".tif":
        raise ValidationError(
            "Формат TIFF не поддерживается. Используйте JPG, PNG, GIF или WebP."
        )
    if ext not in valid_extensions:
        raise ValidationError(
            "Неподдерживаемый формат файла. Используйте JPG, PNG, GIF или WebP."
        )


def validate_image_size(value):
    """Валидатор для проверки размера изображения"""
    max_size = 5 * 1024 * 1024  # 5MB
    if value.size > max_size:
        raise ValidationError(
            f"Размер файла не должен превышать 5MB. Текущий размер: {value.size // 1024}KB"
        )


class City(models.Model):
    """Модель для хранения списка городов"""

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Название города",
        validators=[
            RegexValidator(
                regex=r"^[а-яА-ЯёЁ\s\-]+$",
                message="Город должен содержать только кириллические буквы, пробелы и дефисы",
            )
        ],
    )
    region = models.CharField(max_length=150, blank=True, verbose_name="Регион")
    country = models.CharField(max_length=100, default="Россия", verbose_name="Страна")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}" + (f" ({self.region})" if self.region else "")


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )

    avatar = models.ImageField(
        upload_to="profile_images/%Y/%m/%d/",
        blank=True,
        null=True,
        validators=[validate_image_extension, validate_image_size],
        verbose_name="Аватар профиля",
        help_text="Поддерживаемые форматы: JPG, PNG, GIF, WebP. Максимальный размер: 5MB.",
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="О себе",
        help_text="Максимум 500 символов",
    )

    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Город",
        help_text="Выберите город из списка",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Профиль {self.user.email}"

    def get_avatar_url(self):
        """Возвращает URL аватара или None если аватар не установлен"""
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return None

    def clean(self):
        """Дополнительная валидация на уровне модели"""
        super().clean()

    def save(self, *args, **kwargs):
        """Переопределение save для вызова clean"""
        self.full_clean()
        super().save(*args, **kwargs)

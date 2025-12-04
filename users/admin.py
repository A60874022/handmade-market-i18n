# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Profile, User, City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """Админка для городов"""

    list_display = [
        "name",
        "region",
        "country",
        "is_active",
        "created_at",
        "profiles_count",
    ]
    list_filter = ["is_active", "country", "region", "created_at"]
    search_fields = ["name", "region", "country"]
    ordering = ["name"]
    readonly_fields = ["created_at", "profiles_count"]
    list_editable = ["is_active"]
    list_per_page = 50

    fieldsets = [
        (
            "Основная информация",
            {"fields": ["name", "region", "country", "is_active"]},
        ),
        (
            "Статистика",
            {
                "fields": ["profiles_count", "created_at"],
                "classes": ("collapse",),
            },
        ),
    ]

    def profiles_count(self, obj):
        """Количество профилей в этом городе"""
        return obj.profile_set.count()

    profiles_count.short_description = "Количество профилей"


class ProfileInline(admin.StackedInline):
    """Inline для отображения профиля пользователя"""

    model = Profile
    can_delete = False
    verbose_name_plural = "Профиль"
    fields = ["avatar", "avatar_preview", "bio", "city", "created_at", "updated_at"]
    readonly_fields = ["avatar_preview", "created_at", "updated_at"]
    autocomplete_fields = ["city"]

    def avatar_preview(self, obj):
        if obj.avatar and hasattr(obj.avatar, "url"):
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" />',
                obj.avatar.url,
            )
        return format_html(
            '<div style="width: 100px; height: 100px; background: #f8f9fa; '
            "display: flex; align-items: center; justify-content: center; "
            'border-radius: 5px; color: #6c757d;">👤</div>'
        )

    avatar_preview.short_description = "Предпросмотр аватара"

    def get_queryset(self, request):
        """Оптимизация запроса"""
        return super().get_queryset(request).select_related("city")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для пользователей"""

    list_display = [
        "email",
        "first_name",
        "last_name",
        "city_display",
        "email_verified",
        "is_staff",
        "is_active",
        "date_joined",
    ]
    list_filter = [
        "email_verified",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
        "profile__city",
    ]
    search_fields = ["email", "first_name", "last_name", "profile__city__name"]
    ordering = ["email"]
    readonly_fields = ["date_joined", "last_login", "verification_info"]
    inlines = [ProfileInline]
    list_select_related = ["profile"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Email verification"),
            {
                "fields": ("email_verified", "verification_info"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined"), "classes": ("collapse",)},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )

    def verification_info(self, obj):
        if obj.email_verification_code and obj.email_verification_code_created_at:
            return format_html(
                "Код: <strong>{}</strong><br>Создан: {}",
                obj.email_verification_code,
                obj.email_verification_code_created_at,
            )
        return "Нет активного кода верификации"

    verification_info.short_description = "Информация о верификации"

    def city_display(self, obj):
        """Отображение города пользователя в списке"""
        if hasattr(obj, "profile") and obj.profile.city:
            return obj.profile.city.name
        return "—"

    city_display.short_description = "Город"
    city_display.admin_order_field = "profile__city__name"

    def get_inline_instances(self, request, obj=None):
        """Показываем inline только при редактировании существующего пользователя"""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def get_queryset(self, request):
        """Оптимизация запросов к БД"""
        return super().get_queryset(request).select_related("profile__city")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Админка для профилей пользователей"""

    list_display = [
        "user_email",
        "city",
        "bio_preview",
        "avatar_preview_list",
        "created_at",
    ]
    list_filter = ["city", "city__region", "created_at", "updated_at"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "city__name",
        "bio",
    ]
    readonly_fields = ["user", "avatar_preview", "created_at", "updated_at"]
    list_select_related = ["user", "city"]
    autocomplete_fields = ["city"]
    list_per_page = 25

    fieldsets = [
        ("Пользователь", {"fields": ["user"]}),
        ("Информация профиля", {"fields": ["avatar", "avatar_preview", "bio", "city"]}),
        (
            "Даты",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ("collapse",),
            },
        ),
    ]

    def user_email(self, obj):
        """Email пользователя с ссылкой на редактирование"""
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/users/user/{obj.user.id}/change/",
            obj.user.email,
        )

    user_email.short_description = "Пользователь"
    user_email.admin_order_field = "user__email"

    def bio_preview(self, obj):
        """Сокращенное отображение био"""
        if obj.bio:
            return obj.bio[:75] + "..." if len(obj.bio) > 75 else obj.bio
        return "—"

    bio_preview.short_description = "Био (превью)"

    def avatar_preview(self, obj):
        """Предпросмотр аватара в детальном view"""
        if obj.avatar and hasattr(obj.avatar, "url"):
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px; border-radius: 8px;" />',
                obj.avatar.url,
            )
        return format_html(
            '<div style="width: 200px; height: 200px; background: #f8f9fa; '
            "display: flex; align-items: center; justify-content: center; "
            'border-radius: 8px; color: #6c757d; font-size: 48px;">👤</div>'
        )

    avatar_preview.short_description = "Предпросмотр аватара"

    def avatar_preview_list(self, obj):
        """Предпросмотр аватара в списке"""
        if obj.avatar and hasattr(obj.avatar, "url"):
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 3px;" />',
                obj.avatar.url,
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background: #f8f9fa; '
            "display: flex; align-items: center; justify-content: center; "
            'border-radius: 3px; color: #6c757d; font-size: 20px;">👤</div>'
        )

    avatar_preview_list.short_description = "Аватар"

    def get_readonly_fields(self, request, obj=None):
        """Делаем поле user редактируемым только при создании"""
        if obj:  # редактирование существующего объекта
            return self.readonly_fields + ["user"]
        return self.readonly_fields

    def get_queryset(self, request):
        """Оптимизация запросов к БД"""
        return super().get_queryset(request).select_related("user", "city")

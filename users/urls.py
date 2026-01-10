# users/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views import edit_profile

app_name = "users"

urlpatterns = [
    # Регистрация и подтверждение email через код
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "verify-email-code/",
        views.EmailVerificationCodeView.as_view(),
        name="verify_email_code",
    ),
    path(
        "resend-verification-code/",
        views.ResendVerificationCodeView.as_view(),
        name="resend_verification_code",
    ),
    # Вход и выход
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Профиль
    path("profile/", edit_profile, name="edit_profile"),
    path("delete-account/", views.delete_account, name="delete_account"),
    # Сброс пароля
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="users/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        views.CustomPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path('profile/<int:user_id>/', views.public_profile, name='public_profile'),
]

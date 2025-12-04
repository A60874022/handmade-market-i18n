# users/views.py
import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, FormView, View

from .forms import (
    AccountDeleteForm,
    EmailVerificationForm,
    ProfileEditForm,
    UserEditForm,
    UserLoginForm,
    UserRegistrationForm,
)
from .models import User, City
from .services.email_service import email_service

logger = logging.getLogger(__name__)


class RegisterView(CreateView):
    """
    Представление для регистрации новых пользователей с подтверждением email через код.
    """

    model = User
    form_class = UserRegistrationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:verify_email_code")

    def form_valid(self, form):
        try:
            password = form.cleaned_data["password1"]
            user = getattr(form, "instance", None)

            if user and user.pk:
                # Существующий пользователь (не подтверждён)
                user.set_password(password)  # обновляем пароль
                user.save()
            else:
                # Новый пользователь
                user = form.save(commit=False)
                user.is_active = True
                user.email_verified = False
                user.save()

            # Генерация кода и отправка email
            verification_code = user.generate_verification_code()
            email_service.send_verification_code_email(
                user_email=user.email,
                verification_code=verification_code,
                context={"user_name": user.get_short_name()},
            )

            # Сохраняем в сессии
            self.request.session["user_id_for_verification"] = user.id
            self.request.session["user_email"] = user.email

            messages.success(
                self.request, _("Код подтверждения отправлен на ваш email.")
            )
            return redirect(self.success_url)

        except Exception as e:
            logger.error("Error during user registration: %s", str(e), exc_info=True)
            messages.error(self.request, _("Ошибка при регистрации. Попробуйте позже."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Обработка невалидной формы регистрации.
        """
        email = form.cleaned_data.get("email", "unknown")
        logger.warning(
            "Registration form validation failed for email %s. Errors: %s",
            email,
            form.errors,
        )
        messages.error(self.request, _("Пожалуйста, исправьте ошибки в форме."))
        return super().form_invalid(form)


class EmailVerificationCodeView(FormView):
    """
    Представление для ввода кода подтверждения email
    """

    form_class = EmailVerificationForm
    template_name = "users/emails/verify_email_code.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        """
        Проверяем, что пользователь прошел регистрацию
        """
        if "user_id_for_verification" not in request.session:
            messages.error(request, _("Сначала завершите регистрацию."))
            return redirect("users:register")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Добавляем email пользователя в контекст
        """
        try:
            context = super().get_context_data(**kwargs)
            context["user_email"] = self.request.session.get("user_email")
            return context
        except Exception as e:
            logger.error(
                "Error preparing email verification context: %s", str(e), exc_info=True
            )
            return super().get_context_data(**kwargs)

    def form_valid(self, form):
        """
        Обработка валидной формы с кодом подтверждения
        """
        try:
            user_id = self.request.session.get("user_id_for_verification")
            verification_code = form.cleaned_data["verification_code"]

            user = User.objects.get(id=user_id)

            if user.verify_email_with_code(verification_code):
                # Успешное подтверждение
                login(self.request, user)

                # Очищаем сессию
                self._clear_verification_session()

                messages.success(
                    self.request, _("Email успешно подтвержден! Добро пожаловать!")
                )
                logger.info("Email verified successfully for user: %s", user.email)

                return redirect(self.success_url)
            else:
                messages.error(
                    self.request,
                    _("Неверный код подтверждения или срок его действия истек."),
                )
                return self.form_invalid(form)

        except User.DoesNotExist:
            logger.error(
                "User not found during email verification. User ID: %s", user_id
            )
            messages.error(self.request, _("Пользователь не найден."))
            return self.form_invalid(form)
        except Exception as e:
            logger.error("Error during email verification: %s", str(e), exc_info=True)
            messages.error(self.request, _("Ошибка при подтверждении email."))
            return self.form_invalid(form)

    def _clear_verification_session(self):
        """
        Очищает данные верификации из сессии
        """
        try:
            if "user_id_for_verification" in self.request.session:
                del self.request.session["user_id_for_verification"]
            if "user_email" in self.request.session:
                del self.request.session["user_email"]
        except Exception as e:
            logger.error("Error clearing verification session: %s", str(e))


class ResendVerificationCodeView(View):
    """
    Представление для повторной отправки кода подтверждения
    """

    def post(self, request):
        try:
            user_id = request.session.get("user_id_for_verification")

            if not user_id:
                messages.error(
                    request, _("Сессия истекла. Пожалуйста, зарегистрируйтесь снова.")
                )
                return redirect("users:register")

            user = User.objects.get(id=user_id)
            new_code = user.generate_verification_code()

            email_sent = email_service.send_verification_code_email(
                user_email=user.email,
                verification_code=new_code,
                context={"user_name": user.get_short_name()},
            )

            if email_sent:
                messages.success(
                    request, _("Новый код подтверждения отправлен на ваш email.")
                )
                logger.info("Verification code resent for user: %s", user.email)
            else:
                messages.error(
                    request,
                    _("Не удалось отправить код подтверждения. Попробуйте позже."),
                )
                logger.error(
                    "Failed to resend verification code for user: %s", user.email
                )

            return redirect("users:verify_email_code")

        except User.DoesNotExist:
            logger.error("User not found during code resend. User ID: %s", user_id)
            messages.error(request, _("Пользователь не найден."))
            return redirect("users:register")
        except Exception as e:
            logger.error("Error resending verification code: %s", str(e), exc_info=True)
            messages.error(request, _("Ошибка при отправке кода подтверждения."))
            return redirect("users:verify_email_code")


class CustomLoginView(LoginView):
    """
    Кастомное представление входа.
    Наследуемся от стандартного LoginView и добавляем наши формы и шаблоны.
    """

    form_class = UserLoginForm
    template_name = "users/login.html"
    redirect_authenticated_user = True  # перенаправлять если уже авторизован

    def form_valid(self, form):
        """Добавляем сообщение об успешном входе"""
        try:
            user = form.get_user()
            if user.email_verified:
                messages.success(self.request, _("Успешный вход в систему!"))
                logger.info("User logged in successfully: %s", user.email)
                return super().form_valid(form)
            else:
                messages.error(
                    self.request, _("Пожалуйста, подтвердите ваш email перед входом.")
                )
                return self.form_invalid(form)
        except Exception as e:
            logger.error("Error during user login: %s", str(e), exc_info=True)
            messages.error(self.request, _("Ошибка при входе в систему."))
            return self.form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    """
    Сброс пароля - шаг 1: ввод email
    """

    template_name = "users/password_reset.html"
    email_template_name = "users/password_reset_email.html"
    success_url = reverse_lazy("users:password_reset_done")

    def form_valid(self, form):
        try:
            messages.info(
                self.request,
                _(
                    "Если аккаунт с таким email существует, вы получите инструкции по сбросу пароля."
                ),
            )
            return super().form_valid(form)
        except Exception as e:
            logger.error(
                "Error during password reset request: %s", str(e), exc_info=True
            )
            messages.error(self.request, _("Ошибка при запросе сброса пароля."))
            return self.form_invalid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Сброс пароля - шаг 3: ввод нового пароля
    """

    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")

    def form_valid(self, form):
        try:
            messages.success(self.request, _("Ваш пароль был успешно сброшен!"))
            logger.info("Password reset successfully for user")
            return super().form_valid(form)
        except Exception as e:
            logger.error(
                "Error during password reset confirmation: %s", str(e), exc_info=True
            )
            messages.error(self.request, _("Ошибка при сбросе пароля."))
            return self.form_invalid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Сброс пароля - шаг 4: завершение сброса пароля
    """

    template_name = "users/password_reset_complete.html"


import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


@login_required
def edit_profile(request):
    """
    Представление для редактирования профиля с улучшенной обработкой ошибок
    """
    try:
        user = request.user
        profile = user.profile

        if request.method == "POST":
            user_form = UserEditForm(request.POST, instance=user)
            profile_form = ProfileEditForm(
                request.POST, request.FILES, instance=profile
            )

            if user_form.is_valid() and profile_form.is_valid():
                # Сохраняем пользователя
                user_instance = user_form.save()

                # Сохраняем профиль с обработкой удаления аватара
                profile_instance = profile_form.save(commit=False)

                # Обработка удаления аватара
                if (
                    "avatar-clear" in request.POST
                    and request.POST["avatar-clear"] == "true"
                ):
                    if profile_instance.avatar:
                        # Удаляем старый файл аватара
                        profile_instance.avatar.delete(save=False)
                        profile_instance.avatar = None

                profile_instance.save()

                # Показываем предупреждения если есть
                warnings = profile_form.get_warnings()
                for field, warning_message in warnings.items():
                    messages.warning(request, warning_message, extra_tags="profile")

                # Добавляем extra_tags чтобы идентифицировать сообщение профиля
                messages.success(
                    request,
                    _("✅ Ваш профиль был успешно обновлен!"),
                    extra_tags="profile",
                )

                logger.info(
                    "Profile updated successfully for user: %s",
                    user.email,
                    extra={
                        "user_id": user.id,
                        "changes": {
                            "city_changed": "city" in profile_form.changed_data,
                            "bio_changed": "bio" in profile_form.changed_data,
                            "avatar_changed": "avatar" in profile_form.changed_data,
                        },
                    },
                )
                return redirect("users:edit_profile")

            else:
                # Детальное логирование ошибок
                error_details = {
                    "user_errors": dict(user_form.errors),
                    "profile_errors": dict(profile_form.errors),
                }
                logger.warning(
                    "Profile update failed for user %s. Errors: %s",
                    user.email,
                    error_details,
                    extra={"user_id": user.id},
                )

                messages.error(
                    request,
                    _("❌ Пожалуйста, исправьте ошибки в форме."),
                    extra_tags="profile",
                )

        else:
            user_form = UserEditForm(instance=user)
            profile_form = ProfileEditForm(instance=profile)

        # Получаем список всех городов для datalist
        cities = City.objects.filter(is_active=True).order_by("name")

        context = {
            "user_form": user_form,
            "profile_form": profile_form,
            "cities": cities,  # Добавляем города в контекст
        }
        return render(request, "users/edit_profile.html", context)

    except Exception as e:
        logger.error(
            "Error in edit_profile view for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
            extra={"user_id": request.user.id},
        )
        messages.error(
            request,
            _("⚠️ Произошла ошибка при загрузке страницы редактирования профиля."),
        )
        return redirect("products:catalog")


@login_required
def delete_account(request):
    try:
        if request.method == "POST":
            form = AccountDeleteForm(request.POST, user=request.user)
            if form.is_valid():
                # Сохраняем ссылку на пользователя до выхода
                user_to_delete = request.user
                user_email = user_to_delete.email

                # Выходим пользователя
                logout(request)

                # Удаляем аккаунт (используем сохраненную ссылку)
                user_to_delete.delete()

                messages.success(
                    request,
                    f"Аккаунт {user_email} был успешно удален. Жаль, что вы уходите!",
                )
                logger.info("Account deleted successfully: %s", user_email)
                return redirect("home")
        else:
            form = AccountDeleteForm(user=request.user)

        return render(request, "users/delete_account.html", {"form": form})

    except Exception as e:
        logger.error(
            "Error during account deletion for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении аккаунта.")
        return redirect("users:edit_profile")

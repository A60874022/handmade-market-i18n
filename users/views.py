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
from django.utils.translation import gettext as _
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
from .models import City, User
from .services.email_service import email_service

logger = logging.getLogger(__name__)


class RegisterView(CreateView):
    """
    View for registering new users with email confirmation via code.
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
                # Existing user (unconfirmed)
                user.set_password(password)  # update password
                user.save()
            else:
                # New user
                user = form.save(commit=False)
                user.is_active = True
                user.email_verified = False
                user.save()

            # Generate code and send email
            verification_code = user.generate_verification_code()
            email_service.send_verification_code_email(
                user_email=user.email,
                verification_code=verification_code,
                context={"user_name": user.get_short_name()},
            )

            # Save in session
            self.request.session["user_id_for_verification"] = user.id
            self.request.session["user_email"] = user.email

            messages.success(self.request, _("Verification code sent to your email."))
            return redirect(self.success_url)

        except Exception as e:
            logger.error("Error during user registration: %s", str(e), exc_info=True)
            messages.error(
                self.request, _("Error during registration. Please try again later.")
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Handle invalid registration form.
        """
        email = form.cleaned_data.get("email", "unknown")
        logger.warning(
            "Registration form validation failed for email %s. Errors: %s",
            email,
            form.errors,
        )
        messages.error(self.request, _("Please correct errors in the form."))
        return super().form_invalid(form)


class EmailVerificationCodeView(FormView):
    """
    View for entering email verification code
    """

    form_class = EmailVerificationForm
    template_name = "users/emails/verify_email_code.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        """
        Check that user completed registration
        """
        if "user_id_for_verification" not in request.session:
            messages.error(request, _("Please complete registration first."))
            return redirect("users:register")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Add user email to context
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
        Handle valid form with verification code
        """
        try:
            user_id = self.request.session.get("user_id_for_verification")
            verification_code = form.cleaned_data["verification_code"]

            user = User.objects.get(id=user_id)

            if user.verify_email_with_code(verification_code):
                # Successful confirmation
                login(self.request, user)

                # Clear session
                self._clear_verification_session()

                messages.success(
                    self.request, _("Email successfully verified! Welcome!")
                )
                logger.info("Email verified successfully for user: %s", user.email)

                return redirect(self.success_url)
            else:
                messages.error(
                    self.request,
                    _("Invalid verification code or it has expired."),
                )
                return self.form_invalid(form)

        except User.DoesNotExist:
            logger.error(
                "User not found during email verification. User ID: %s", user_id
            )
            messages.error(self.request, _("User not found."))
            return self.form_invalid(form)
        except Exception as e:
            logger.error("Error during email verification: %s", str(e), exc_info=True)
            messages.error(self.request, _("Error confirming email."))
            return self.form_invalid(form)

    def _clear_verification_session(self):
        """
        Clear verification data from session
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
    View for resending verification code
    """

    def post(self, request):
        try:
            user_id = request.session.get("user_id_for_verification")

            if not user_id:
                messages.error(request, _("Session expired. Please register again."))
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
                    request, _("New verification code sent to your email.")
                )
                logger.info("Verification code resent for user: %s", user.email)
            else:
                messages.error(
                    request,
                    _("Failed to send verification code. Please try again later."),
                )
                logger.error(
                    "Failed to resend verification code for user: %s", user.email
                )

            return redirect("users:verify_email_code")

        except User.DoesNotExist:
            logger.error("User not found during code resend. User ID: %s", user_id)
            messages.error(request, _("User not found."))
            return redirect("users:register")
        except Exception as e:
            logger.error("Error resending verification code: %s", str(e), exc_info=True)
            messages.error(request, _("Error sending verification code."))
            return redirect("users:verify_email_code")


class CustomLoginView(LoginView):
    """
    Custom login view.
    Inherits from standard LoginView and adds our forms and templates.
    """

    form_class = UserLoginForm
    template_name = "users/login.html"
    redirect_authenticated_user = True  # redirect if already authenticated

    def form_valid(self, form):
        """Add successful login message"""
        try:
            user = form.get_user()
            if user.email_verified:
                messages.success(self.request, _("Successfully logged in!"))
                logger.info("User logged in successfully: %s", user.email)
                return super().form_valid(form)
            else:
                messages.error(
                    self.request, _("Please verify your email before logging in.")
                )
                return self.form_invalid(form)
        except Exception as e:
            logger.error("Error during user login: %s", str(e), exc_info=True)
            messages.error(self.request, _("Error logging in."))
            return self.form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    """
    Password reset - step 1: enter email
    """

    template_name = "users/password_reset.html"
    email_template_name = "users/password_reset_email.html"
    success_url = reverse_lazy("users:password_reset_done")

    def form_valid(self, form):
        try:
            messages.info(
                self.request,
                _(
                    "If an account exists with this email, you will receive password reset instructions."
                ),
            )
            return super().form_valid(form)
        except Exception as e:
            logger.error(
                "Error during password reset request: %s", str(e), exc_info=True
            )
            messages.error(self.request, _("Error requesting password reset."))
            return self.form_invalid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset - step 3: enter new password
    """

    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")

    def form_valid(self, form):
        try:
            messages.success(
                self.request, _("Your password has been successfully reset!")
            )
            logger.info("Password reset successfully for user")
            return super().form_valid(form)
        except Exception as e:
            logger.error(
                "Error during password reset confirmation: %s", str(e), exc_info=True
            )
            messages.error(self.request, _("Error resetting password."))
            return self.form_invalid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset - step 4: password reset complete
    """

    template_name = "users/password_reset_complete.html"


@login_required
def edit_profile(request):
    """
    View for editing profile with improved error handling
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
                # Save user
                user_instance = user_form.save()

                # Save profile with avatar deletion handling
                profile_instance = profile_form.save(commit=False)

                # Handle avatar deletion
                if (
                    "avatar-clear" in request.POST
                    and request.POST["avatar-clear"] == "true"
                ):
                    if profile_instance.avatar:
                        # Delete old avatar file
                        profile_instance.avatar.delete(save=False)
                        profile_instance.avatar = None

                profile_instance.save()

                # Show warnings if any
                warnings = profile_form.get_warnings()
                for field, warning_message in warnings.items():
                    messages.warning(request, warning_message, extra_tags="profile")

                # Add extra_tags to identify profile message
                messages.success(
                    request,
                    _("✅ Your profile has been successfully updated!"),
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
                # Detailed error logging
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
                    _("❌ Please correct errors in the form."),
                    extra_tags="profile",
                )

        else:
            user_form = UserEditForm(instance=user)
            profile_form = ProfileEditForm(instance=profile)

        # Get list of all cities for datalist
        cities = City.objects.filter(is_active=True).order_by("name")

        context = {
            "user_form": user_form,
            "profile_form": profile_form,
            "cities": cities,  # Add cities to context
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
            _("⚠️ An error occurred while loading the profile editing page."),
        )
        return redirect("products:catalog")


@login_required
def delete_account(request):
    try:
        if request.method == "POST":
            form = AccountDeleteForm(request.POST, user=request.user)
            if form.is_valid():
                # Save reference to user before logout
                user_to_delete = request.user
                user_email = user_to_delete.email

                # Logout user
                logout(request)

                # Delete account (using saved reference)
                user_to_delete.delete()

                messages.success(
                    request,
                    _(
                        f"Account {user_email} has been successfully deleted. We're sorry to see you go!"
                    ),
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
        messages.error(request, _("Error deleting account."))
        return redirect("users:edit_profile")

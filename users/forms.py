import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _

from .models import Profile, User, City


def validate_password_no_russian(value):
    """
    Password validator: check for absence of Russian letters.
    """
    russian_chars_pattern = re.compile("[а-яёА-ЯЁ]")
    if russian_chars_pattern.search(value):
        raise ValidationError(
            _("Password must not contain Russian letters."),
            code="password_contains_russian",
        )


class UserRegistrationForm(UserCreationForm):
    """
    Custom user registration form with extended validation.
    """

    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("your.email@example.com"),
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
        label=_("Email address"),
        help_text=_("Enter a valid email address."),
        validators=[validate_email],
    )

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        """
        Form initialization with field customization.
        """
        super().__init__(*args, **kwargs)

        # Customize password1 field
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": _("Create a strong password"),
                "autocomplete": "new-password",
            }
        )
        self.fields["password1"].validators.append(validate_password_no_russian)

        # Customize password2 field
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": _("Repeat your password"),
                "autocomplete": "new-password",
            }
        )

        # Set labels and help texts
        self.fields["password1"].label = _("Password")
        self.fields["password2"].label = _("Password confirmation")
        self.fields["password1"].help_text = _(
            "Password must contain at least 8 characters, "
            "not consist only of numbers and not be too simple. "
            "Russian letters are not allowed."
        )

    def clean_email(self):
        email = self.cleaned_data.get("email").lower().strip()
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                raise ValidationError(
                    _("User with this email already exists."),
                    code="duplicate_email",
                )
            else:
                # Email exists but not verified - use existing user
                self.instance = user
        except User.DoesNotExist:
            pass
        return email

    def clean_password1(self):
        """
        Password validation.
        """
        password1 = self.cleaned_data.get("password1")

        # Check for Russian characters
        validate_password_no_russian(password1)

        # Standard Django password validation
        from django.contrib.auth.password_validation import validate_password

        validate_password(password1)

        return password1

    def save(self, commit=True):
        """
        Save user with normalized email.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()

        if commit:
            user.save()

        return user


class UserLoginForm(AuthenticationForm):
    """
    User login form.
    Inherits from AuthenticationForm, changes username to email.
    """

    username = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("your.email@example.com"),
                "autocomplete": "email",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Password"),
                "autocomplete": "current-password",
            }
        )
    )

    error_messages = {
        "invalid_login": _(
            "Please enter a correct %(username)s and password. "
            "Note that both fields may be case-sensitive."
        ),
        "inactive": _("This account is inactive."),
        "email_not_verified": _("Please verify your email address before logging in."),
    }

    def confirm_login_allowed(self, user):
        """
        Check if user can log in.
        """
        if not user.email_verified:
            raise forms.ValidationError(
                self.error_messages["email_not_verified"],
                code="email_not_verified",
            )
        super().confirm_login_allowed(user)


class EmailVerificationForm(forms.Form):
    """
    Form for entering email verification code
    """

    verification_code = forms.CharField(
        label=_("Verification code"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter 6-digit code"),
                "maxlength": "6",
                "pattern": "[0-9]{6}",
            }
        ),
        help_text=_("Enter 6-digit code sent to your email"),
    )

    def clean_verification_code(self):
        """Validate verification code"""
        code = self.cleaned_data.get("verification_code", "").strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError(
                _("Code must consist of 6 digits."), code="invalid_code_format"
            )
        return code


class UserEditForm(forms.ModelForm):
    # Remove password field so user doesn't see it in plain text
    password = None

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
        )  # Add fields as needed


class ProfileEditForm(forms.ModelForm):
    # Override bio field to add character counter
    bio = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": _("Tell about yourself and your creativity..."),
                "class": "form-control",
                "maxlength": "500",
                "data-max-length": "500",
            }
        ),
        label=_("About me"),
        help_text=_("Maximum 500 characters"),
    )

    # Override city field for autocomplete text input
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.HiddenInput(),  # Hidden field for storing selected city ID
    )

    # New field for autocomplete text input
    city_search = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Start typing city name..."),
                "list": "cities-datalist",
                "autocomplete": "off",
                "id": "city-search-input",
            }
        ),
        label=_("City"),
        help_text=_("Start typing city name and select from list"),
    )

    # Override avatar field to add validation
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png,.gif,.webp",
                "data-max-size": "5242880",  # 5MB in bytes
            }
        ),
        label=_("Profile avatar"),
    )

    class Meta:
        model = Profile
        fields = ("avatar", "bio", "city")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for validation
        self.fields["email"] = forms.EmailField(
            required=True,
            widget=forms.EmailInput(
                attrs={"class": "form-control", "placeholder": _("Enter your email")}
            ),
            label=_("Email address"),
        )

        # Update queryset for city field in init to always get current data
        self.fields["city"].queryset = City.objects.filter(is_active=True).order_by(
            "name"
        )

        # Set initial value for city search field
        if self.instance and self.instance.city:
            self.fields["city_search"].initial = self.instance.city.name

    def clean(self):
        """General form validation"""
        cleaned_data = super().clean()

        # Check that existing city is selected
        city_search = cleaned_data.get("city_search")
        city_id = cleaned_data.get("city")

        if city_search and not city_id:
            try:
                city = City.objects.get(name=city_search)
                cleaned_data["city"] = city
            except City.DoesNotExist:
                self.add_error("city_search", _("Select city from list"))

        # Can add cross-field validations if needed
        city = cleaned_data.get("city")
        bio = cleaned_data.get("bio")

        # Example: if city specified but no bio - warning
        if city and not bio:
            self.add_warning(
                "bio",
                _("We recommend adding information about yourself for better profile presentation."),
            )

        return cleaned_data

    def clean_avatar(self):
        """Custom avatar field cleaning"""
        avatar = self.cleaned_data.get("avatar")

        if avatar:
            # Additional extension check (just in case)
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext == ".tiff" or ext == ".tif":
                raise forms.ValidationError(
                    _("TIFF format is not supported. Use JPG, PNG, GIF or WebP.")
                )

            # Additional size check
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_("File size must not exceed 5MB."))

        return avatar

    def add_warning(self, field, message):
        """Method for adding warnings (not errors)"""
        if not hasattr(self, "_warnings"):
            self._warnings = {}
        self._warnings[field] = message

    def get_warnings(self):
        """Get form warnings"""
        return getattr(self, "_warnings", {})


class AccountDeleteForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("I understand this action cannot be undone"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter your password to confirm"),
            }
        ),
        label=_("Current password"),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Extract user from kwargs
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if self.user and not self.user.check_password(password):
            raise forms.ValidationError(_("Incorrect password"))
        return password
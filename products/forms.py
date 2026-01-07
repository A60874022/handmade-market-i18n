from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _

from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "title", "description", "price"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("For example: Knitted wool hat"),
                    "maxlength": "60",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": _("Describe your product, materials, sizes..."),
                    "maxlength": "300",
                }
            ),
            # CHANGED: NumberInput to TextInput to remove browser restrictions
            "price": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "inputmode": "numeric",  # Shows numeric keyboard on mobile
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Note 18: Add validators for Latin characters
        self.fields["title"].validators.append(
            RegexValidator(
                regex="^[a-zA-Z0-9\s\-\!\.\(\)]+$",
                message=_(
                    "Title must contain only Latin characters, numbers and spaces"
                ),
            )
        )
        self.fields["description"].validators.append(
            RegexValidator(
                regex="^[a-zA-Z0-9\s\-\!\.\(\)\,\:\;]+$",
                message=_(
                    "Description must contain only Latin characters, numbers and punctuation"
                ),
            )
        )

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is None or price == "":
            raise forms.ValidationError(_("Enter product price"))

        try:
            # Convert string to number
            price_int = int(price)
        except (ValueError, TypeError):
            raise forms.ValidationError(_("Enter correct price (numbers only)"))

        # Check price limits
        if price_int < 1:
            raise forms.ValidationError(_("Price must be at least 1 ruble"))

        if price_int > 5000000:
            raise forms.ValidationError(_("Price cannot exceed 5,000,000 euros"))

        return price_int

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title:
            if len(title) > 60:
                raise forms.ValidationError(_("Title cannot exceed 60 characters"))
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            if len(description) > 300:
                raise forms.ValidationError(
                    _("Description cannot exceed 300 characters")
                )
        return description


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main"]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "is_main": forms.CheckboxInput(
                attrs={"class": "form-check-input main-image-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image field optional for existing records
        if self.instance and self.instance.pk:
            self.fields["image"].required = False


# Note 20: Clarify number of photos (up to 4 inclusive)
ProductImageFormSet = forms.inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=4,  # Can upload up to 4 photos inclusive
    can_delete=True,
    max_num=4,  # Maximum 4 photos
)

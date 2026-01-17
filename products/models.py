import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    LANGUAGES = [
        ('en', _('English')),
        ('fr', _('French')),
        ('de', _('German')),
        # add other languages as needed
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.SlugField(max_length=100, verbose_name=_("URL"))
    language_code = models.CharField(
        max_length=10,
        choices=LANGUAGES,
        default='en',
        verbose_name=_("Language Code")
    )
    translation_group = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Translation Group"),
        db_index=True
    )
    # Keep original field for compatibility
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        # Ensure uniqueness within translation groups
        unique_together = [['translation_group', 'language_code']]
        # Also slug uniqueness within language
        constraints = [
            models.UniqueConstraint(
                fields=['language_code', 'slug'],
                name='unique_slug_per_language'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_language_code_display()})"

    def save(self, *args, **kwargs):
        # Note 17: Save name with capital letter
        if self.name:
            self.name = self.name.capitalize()
        
        # Automatically generate slug from name if not specified
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validation to prevent duplicates"""
        super().clean()
        
        # Check that slug is unique for the given language
        if Category.objects.filter(
            language_code=self.language_code,
            slug=self.slug
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                _('A category with this slug already exists for the selected language.')
            )

    @property
    def base_slug(self):
        """Return base slug without language suffix"""
        # Remove language suffix if present
        if self.slug.endswith(f'-{self.language_code}'):
            return self.slug[:-len(f'-{self.language_code}')]
        return self.slug

    @classmethod
    def get_translation_group_categories(cls, translation_group):
        """Get all category translations"""
        return cls.objects.filter(
            translation_group=translation_group,
            is_active=True
        )

    @classmethod
    def get_category_in_language(cls, translation_group, language_code):
        """Get category in specific language"""
        return cls.objects.filter(
            translation_group=translation_group,
            language_code=language_code,
            is_active=True
        ).first()

    def get_translations(self):
        """Get all translations of this category"""
        return self.__class__.objects.filter(
            translation_group=self.translation_group,
            is_active=True
        ).exclude(pk=self.pk)


class Product(models.Model):
    MAX_PRICE = 5000000

    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("Master"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Category"),
    )
    title = models.CharField(
        max_length=60,
        verbose_name=_("Title"),
        validators=[
            RegexValidator(
                regex="^[a-zA-Z0-9\s\-\!\.\(\)]+$",
                message=_(
                    "Title must contain only Latin characters, numbers and spaces"
                ),
            )
        ],
    )
    description = models.TextField(
        max_length=300,
        verbose_name=_("Description"),
        validators=[
            RegexValidator(
                regex="^[a-zA-Z0-9\s\-\!\.\(\)\,\:\;]+$",
                message=_(
                    "Description must contain only Latin characters, numbers and punctuation"
                ),
            )
        ],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price"),
        validators=[
            MinValueValidator(1, message=_("Price must be at least 1 euro")),
            MaxValueValidator(
                MAX_PRICE,
                message=_("Price cannot exceed %(max_price)s euros")
                % {"max_price": MAX_PRICE},
            ),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_approved = models.BooleanField(
        default=False, verbose_name=_("Approved by moderator")
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Return absolute URL for product"""
        return reverse("products:product_detail", kwargs={"pk": self.pk})

    @property
    def city(self):
        """Automatically get city from master profile"""
        if hasattr(self.master, "profile") and self.master.profile.city:
            return self.master.profile.city
        return None

    def get_city_display(self):
        """Return display name of city"""
        city = self.city
        if city:
            return city.name
        return _("City not specified")

    def get_main_image(self):
        """Return main product image"""
        try:
            main_image = self.images.filter(is_main=True).first()
            if main_image:
                return main_image
            return self.images.first()
        except:
            return None

    def has_images(self):
        """Check if product has images"""
        return self.images.exists()

    def is_visible(self):
        """Product is visible if active and approved"""
        return self.is_active and self.is_approved


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="product_images/", verbose_name=_("Image"))
    is_main = models.BooleanField(default=False, verbose_name=_("Main image"))

    class Meta:
        verbose_name = _("Product image")
        verbose_name_plural = _("Product images")

    def __str__(self):
        return _("Image of %(title)s") % {"title": self.product.title}

    def save(self, *args, **kwargs):
        # Note 21: Limit to one main photo
        if self.is_main:
            # Remove is_main flag from all other images of this product
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(
                pk=self.pk
            ).update(is_main=False)
        super().save(*args, **kwargs)


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("Favorite")
        verbose_name_plural = _("Favorite products")
        unique_together = ["user", "product"]

    def __str__(self):
        return _("%(email)s - %(title)s") % {
            "email": self.user.email,
            "title": self.product.title
        }
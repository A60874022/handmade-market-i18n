from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Number of empty forms for adding images
    fields = ["image", "is_main"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "master",
        "category",
        "price",
        "is_active",
        "is_approved",
        "created_at",
    ]
    list_filter = ["category", "is_active", "is_approved", "created_at"]
    search_fields = ["title", "master__email"]
    list_editable = ["is_active", "is_approved"]
    inlines = [ProductImageInline]
    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("master", "category", "title", "description", "price")},
        ),
        (_("Status"), {"fields": ("is_active", "is_approved")}),
    )
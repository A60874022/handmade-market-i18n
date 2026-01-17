from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Number of empty forms for adding images
    fields = ["image", "is_main"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "language_code", "translation_group", "is_active"]
    list_filter = ["language_code", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


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
    search_fields = ["title", "master__email", "description"]
    list_editable = ["is_active", "is_approved"]
    inlines = [ProductImageInline]
    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("master", "category", "title", "description", "price")},
        ),
        (_("Status"), {"fields": ("is_active", "is_approved")}),
        (_("Dates"), {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )
    readonly_fields = ["created_at", "updated_at"]
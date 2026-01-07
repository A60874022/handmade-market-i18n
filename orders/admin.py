# orders/admin.py
from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    """Inline для отображения товаров в корзине"""

    model = CartItem
    extra = 0
    readonly_fields = ["added_at", "total_price"]
    fields = ["product", "quantity", "total_price", "added_at"]
    raw_id_fields = ["product"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Админка для корзин"""

    list_display = ["user", "total_quantity", "total_price", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    readonly_fields = ["created_at", "updated_at", "total_price", "total_quantity"]
    inlines = [CartItemInline]

    def total_quantity(self, obj):
        return obj.total_quantity

    total_quantity.short_description = "Общее количество"

    def total_price(self, obj):
        return f"{obj.total_price} €"

    total_price.short_description = "Общая стоимость"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Админка для элементов корзины"""

    list_display = ["cart", "product", "quantity", "total_price", "added_at"]
    list_filter = ["added_at", "cart__user"]
    search_fields = ["cart__user__email", "product__title"]
    readonly_fields = ["added_at", "total_price"]
    raw_id_fields = ["cart", "product"]

    def total_price(self, obj):
        return f"{obj.total_price} €"

    total_price.short_description = "Общая стоимость"


class OrderItemInline(admin.TabularInline):
    """Inline для отображения товаров в заказе"""

    model = OrderItem
    extra = 0
    readonly_fields = ["total_price"]
    fields = ["product", "quantity", "price_at_moment", "total_price"]
    raw_id_fields = ["product"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админка для заказов"""

    list_display = [
        "id",
        "customer",
        "status",
        "total_amount",
        "created_at",
        "updated_at",
    ]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = ["customer__email", "id"]
    readonly_fields = ["created_at", "updated_at", "total_amount"]
    inlines = [OrderItemInline]
    list_editable = ["status"]
    date_hierarchy = "created_at"

    fieldsets = [
        ("Основная информация", {"fields": ["customer", "status", "total_amount"]}),
        ("Даты", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    def total_amount_display(self, obj):
        return f"{obj.total_amount} €"

    total_amount_display.short_description = "Общая сумма"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Админка для элементов заказа"""

    list_display = ["order", "product", "quantity", "price_at_moment", "total_price"]
    list_filter = ["order__status", "order__created_at"]
    search_fields = ["order__id", "product__title", "order__customer__email"]
    readonly_fields = ["total_price"]
    raw_id_fields = ["order", "product"]

    def total_price(self, obj):
        return f"{obj.total_price} €"

    total_price.short_description = "Общая стоимость"

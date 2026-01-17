from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from products.models import Product

User = get_user_model()


class Cart(models.Model):
    """Shopping cart"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return _("Cart of %(email)s") % {"email": self.user.email}

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")


class CartItem(models.Model):
    """Cart item"""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Added at"))

    class Meta:
        unique_together = ["cart", "product"]
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """Order"""

    STATUS_CHOICES = [
        ("placed", _("Placed")),
        ("in_progress", _("In progress")),
        ("shipped", _("Shipped")),
        ("delivered", _("Delivered")),
        ("cancelled", _("Cancelled")),
    ]

    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="orders",
        verbose_name=_("Customer")
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="placed",
        verbose_name=_("Status")
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name=_("Total amount")
    )

    def __str__(self):
        return _("Order #%(id)s - %(email)s") % {
            "id": self.id,
            "email": self.customer.email,
        }

    def update_total_amount(self):
        self.total_amount = sum(item.total_price for item in self.items.all())
        self.save()

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")


class OrderItem(models.Model):
    """Order item"""

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name="items",
        verbose_name=_("Order")
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name=_("Product")
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity")
    )
    price_at_moment = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name=_("Price at moment")
    )

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"

    @property
    def total_price(self):
        return self.price_at_moment * self.quantity

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
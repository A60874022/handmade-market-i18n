import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from notifications.services import NotificationService
from products.models import Product

from .models import Cart, CartItem, Order, OrderItem

logger = logging.getLogger(__name__)


@login_required
def cart_view(request):
    """View cart"""
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related(
            "product", "product__master", "product__category"
        ).all()

        context = {
            "cart": cart,
            "cart_items": cart_items,
        }
        return render(request, "orders/cart.html", context)

    except Exception as e:
        logger.error(
            "Error loading cart for user %s: %s", request.user.id, str(e), exc_info=True
        )
        messages.error(request, _("Error loading cart"))
        return redirect("products:catalog")


@login_required
def add_to_cart(request, pk):
    """Add product to cart"""
    try:
        product = get_object_or_404(Product, id=pk, is_active=True)

        # RESTORE CHECK: master cannot buy their own products
        if product.master == request.user:
            messages.error(request, _("You cannot buy your own products"))
            return redirect("products:product_detail", pk=product.id)

        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if this product is already in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": 1}
        )

        if not item_created:
            # If product already in cart, increase quantity
            cart_item.quantity += 1
            cart_item.save()
            messages.success(
                request,
                _('Quantity of product "%(title)s" increased to %(quantity)d')
                % {"title": product.title, "quantity": cart_item.quantity},
            )
        else:
            messages.success(
                request,
                _('Product "%(title)s" added to cart!') % {"title": product.title},
            )

        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error adding product %s to cart for user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error adding product to cart"))
        return redirect("products:product_detail", pk=pk)


@login_required
def update_cart_item(request, item_id):
    """Update product quantity in cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if request.method == "POST":
            quantity = int(request.POST.get("quantity", 1))

            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()
                messages.success(request, _("Product removed from cart"))

        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error updating cart item %s for user %s: %s",
            item_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error updating cart"))
        return redirect("orders:cart_view")


@login_required
def remove_from_cart(request, item_id):
    """Remove product from cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_title = cart_item.product.title
        cart_item.delete()

        messages.success(
            request,
            _('Product "%(title)s" removed from cart') % {"title": product_title},
        )
        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error removing cart item %s for user %s: %s",
            item_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error removing product from cart"))
        return redirect("orders:cart_view")


@login_required
@transaction.atomic
def create_order(request):
    """Create order from cart"""
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.select_related("product").all()

        if not cart_items:
            messages.error(request, _("Your cart is empty"))
            return redirect("orders:cart_view")

        own_products_removed = False
        items_to_remove = []

        for item in cart_items:
            # Check that product is active
            if not item.product.is_active:
                messages.error(
                    request,
                    _('Product "%(title)s" is no longer available')
                    % {"title": item.product.title},
                )
                return redirect("orders:cart_view")

            # Check that product does not belong to user
            if item.product.master == request.user:
                items_to_remove.append(item)
                own_products_removed = True

        # Remove user's own products
        for item in items_to_remove:
            item.delete()

        # Update product list after removal
        cart_items = cart.items.select_related("product").all()

        # If cart is empty after removing own products
        if not cart_items:
            if own_products_removed:
                messages.error(
                    request,
                    _(
                        "You cannot buy your own products. These products have been removed from cart."
                    ),
                )
            else:
                messages.error(request, _("Your cart is empty"))
            return redirect("orders:cart_view")

        if own_products_removed:
            messages.warning(
                request,
                _(
                    "Your own products have been removed from cart before order placement."
                ),
            )

        order = Order.objects.create(customer=request.user, status="placed")
        total_amount = 0
        masters_notified = set()

        for cart_item in cart_items:
            order_item = OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price_at_moment=cart_item.product.price,
            )

            total_amount += cart_item.product.price * cart_item.quantity

            # Create notification for master (if it's not our own product)
            master = cart_item.product.master

            # Additional check (just in case)
            if master.id != request.user.id and master.id not in masters_notified:
                NotificationService.create_order_notification(order, master)
                masters_notified.add(master.id)

        # Update total order amount
        order.total_amount = total_amount
        order.save()
        cart.items.all().delete()

        logger.info(
            "Order created successfully. Order ID: %s, User: %s, Amount: %s",
            order.id,
            request.user.id,
            total_amount,
        )

        messages.success(
            request,
            _("Order #%(id)s successfully placed! Amount: %(amount)s €")
            % {"id": order.id, "amount": total_amount},
        )
        return redirect("orders:purchase_orders")

    except Exception as e:
        logger.error(
            "Error creating order for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(
            request, _("Error creating order: %(error)s") % {"error": str(e)}
        )
        return redirect("orders:cart_view")


@login_required
def purchase_orders(request):
    """Purchases page (orders as buyer)"""
    try:
        orders = (
            Order.objects.filter(customer=request.user)
            .prefetch_related("items__product__images", "items__product__master")
            .order_by("-created_at")
        )

        context = {"orders": orders}
        return render(request, "orders/purchase_orders.html", context)

    except Exception as e:
        logger.error(
            "Error loading purchase orders for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error loading orders"))
        return redirect("products:catalog")


@login_required
def sale_orders(request):
    """Sales page (orders for master's products)"""
    try:
        # Orders containing this master's products
        orders = (
            Order.objects.filter(items__product__master=request.user)
            .distinct()
            .prefetch_related("items__product__images", "customer")
            .order_by("-created_at")
        )

        context = {"orders": orders}
        return render(request, "orders/sale_orders.html", context)

    except Exception as e:
        logger.error(
            "Error loading sale orders for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error loading orders"))
        return redirect("products:catalog")


@login_required
@transaction.atomic
def delete_order(request, order_id):
    """
    Delete order by buyer with checks and notifications
    """
    try:
        # Find order and check that it belongs to current user
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # Save information for message
        order_id_val = order.id
        order_status = order.status

        # Additional check: cannot delete delivered orders
        if order.status == "delivered":
            messages.error(request, _("Cannot delete delivered order."))
            return redirect("orders:purchase_orders")

        # Create notifications for masters before deletion (if not our own product)
        masters_notified = set()
        for item in order.items.all():
            master = item.product.master
            if master.id != request.user.id and master.id not in masters_notified:
                try:
                    # Notify master about order cancellation by buyer
                    NotificationService.create_cancellation_notification(
                        order, master, request.user
                    )
                    masters_notified.add(master.id)
                except Exception as e:
                    logger.error(
                        "Error creating cancellation notification for master %s: %s",
                        master.id,
                        str(e),
                    )

        # Delete order
        order.delete()

        logger.info(
            "Order deleted by customer. Order ID: %s, User: %s",
            order_id_val,
            request.user.id,
        )

        messages.success(
            request, _("Order #%(id)s successfully deleted.") % {"id": order_id_val}
        )

    except Order.DoesNotExist:
        logger.error(
            "Order not found for deletion. Order ID: %s, User: %s",
            order_id,
            request.user.id,
        )
        messages.error(
            request, _("Order not found or you don't have permission to delete it.")
        )
    except Exception as e:
        logger.error(
            "Error deleting order %s by user %s: %s",
            order_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(
            request, _("Error deleting order: %(error)s") % {"error": str(e)}
        )

    return redirect("orders:purchase_orders")


@login_required
@transaction.atomic
def delete_sale_order(request, order_id):
    """
    Delete order by master with improved logic
    """
    try:
        # Get order
        order = get_object_or_404(Order, id=order_id)

        # Check that order contains this master's products
        master_items = order.items.filter(product__master=request.user)
        if not master_items.exists():
            messages.error(request, _("This order does not contain your products."))
            return redirect("orders:sale_orders")

        # Notify buyer about order cancellation by master (if not our own order)
        if order.customer.id != request.user.id:
            try:
                NotificationService.create_master_cancellation_notification(
                    order, request.user
                )
            except Exception as e:
                logger.error(
                    "Error creating master cancellation notification for customer %s: %s",
                    order.customer.id,
                    str(e),
                )

        order_id_val = order.id
        order.delete()

        logger.info(
            "Sale order deleted by master. Order ID: %s, User: %s",
            order_id_val,
            request.user.id,
        )

        messages.success(
            request,
            _("Order #%(id)s has been successfully deleted.") % {"id": order_id_val},
        )

    except Order.DoesNotExist:
        logger.error(
            "Sale order not found for deletion. Order ID: %s, User: %s",
            order_id,
            request.user.id,
        )
        messages.error(request, _("Order not found."))
    except Exception as e:
        logger.error(
            "Error deleting sale order %s by user %s: %s",
            order_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(
            request,
            _("An error occurred while deleting order: %(error)s") % {"error": str(e)},
        )

    return redirect("orders:sale_orders")
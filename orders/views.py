import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from notifications.services import NotificationService
from products.models import Product

from .models import Cart, CartItem, Order, OrderItem

logger = logging.getLogger(__name__)


@login_required
def cart_view(request):
    """Просмотр корзины"""
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
        messages.error(request, "Ошибка при загрузке корзины")
        return redirect("products:catalog")


@login_required
def add_to_cart(request, pk):
    """Добавление товара в корзину"""
    try:
        product = get_object_or_404(Product, id=pk, is_active=True)

        # ВОССТАНАВЛИВАЕМ ПРОВЕРКУ: мастер не может покупать свои товары
        if product.master == request.user:
            messages.error(request, "Вы не можете покупать свои собственные товары")
            return redirect("products:product_detail", pk=product.id)

        cart, created = Cart.objects.get_or_create(user=request.user)

        # Проверяем, есть ли уже этот товар в корзине
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": 1}
        )

        if not item_created:
            # Если товар уже есть в корзине, увеличиваем количество
            cart_item.quantity += 1
            cart_item.save()
            messages.success(
                request,
                f'Количество товара "{product.title}" увеличено до {cart_item.quantity}',
            )
        else:
            messages.success(request, f'Товар "{product.title}" добавлен в корзину!')

        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error adding product %s to cart for user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при добавлении товара в корзину")
        return redirect("products:product_detail", pk=pk)


@login_required
def update_cart_item(request, item_id):
    """Обновление количества товара в корзине"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if request.method == "POST":
            quantity = int(request.POST.get("quantity", 1))

            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()
                messages.success(request, "Товар удален из корзины")

        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error updating cart item %s for user %s: %s",
            item_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при обновлении корзины")
        return redirect("orders:cart_view")


@login_required
def remove_from_cart(request, item_id):
    """Удаление товара из корзины"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_title = cart_item.product.title
        cart_item.delete()

        messages.success(request, f'Товар "{product_title}" удален из корзины')
        return redirect("orders:cart_view")

    except Exception as e:
        logger.error(
            "Error removing cart item %s for user %s: %s",
            item_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении товара из корзины")
        return redirect("orders:cart_view")


@login_required
@transaction.atomic
def create_order(request):
    """Создание заказа из корзины"""
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.select_related("product").all()

        if not cart_items:
            messages.error(request, "Ваша корзина пуста")
            return redirect("orders:cart_view")
        own_products_removed = False
        items_to_remove = []

        for item in cart_items:
            # Проверяем, что товар активен
            if not item.product.is_active:
                messages.error(
                    request, f'Товар "{item.product.title}" больше не доступен'
                )
                return redirect("orders:cart_view")

            # Проверяем, что товар не принадлежит пользователю
            if item.product.master == request.user:
                items_to_remove.append(item)
                own_products_removed = True

        # Удаляем собственные товары пользователя
        for item in items_to_remove:
            item.delete()

        # Обновляем список товаров после удаления
        cart_items = cart.items.select_related("product").all()

        # Если после удаления своих товаров корзина пуста
        if not cart_items:
            if own_products_removed:
                messages.error(
                    request,
                    "Вы не можете покупать свои собственные товары. Эти товары были удалены из корзины.",
                )
            else:
                messages.error(request, "Ваша корзина пуста")
            return redirect("orders:cart_view")
        if own_products_removed:
            messages.warning(
                request,
                "Ваши собственные товары были удалены из корзины перед оформлением заказа.",
            )

        order = Order.objects.create(customer=request.user, status="оформлен")
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

            # Создаем уведомление для мастера (если это не наш собственный товар)
            master = cart_item.product.master

            # Дополнительная проверка (на всякий случай)
            if master.id != request.user.id and master.id not in masters_notified:
                NotificationService.create_order_notification(order, master)
                masters_notified.add(master.id)

        # Обновляем общую сумму заказа
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
            request, f"Заказ #{order.id} успешно оформлен! Сумма: {total_amount} ₽"
        )
        return redirect("orders:purchase_orders")

    except Exception as e:
        logger.error(
            "Error creating order for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, f"Ошибка при создании заказа: {str(e)}")
        return redirect("orders:cart_view")


@login_required
def purchase_orders(request):
    """Страница покупок (заказы как покупателя)"""
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
        messages.error(request, "Ошибка при загрузке заказов")
        return redirect("products:catalog")


@login_required
def sale_orders(request):
    """Страница продаж (заказы на товары мастера)"""
    try:
        # Заказы, где есть товары этого мастера
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
        messages.error(request, "Ошибка при загрузке заказов")
        return redirect("products:catalog")


@login_required
@transaction.atomic
def delete_order(request, order_id):
    """
    Удаление заказа покупателем с проверками и уведомлениями
    """
    try:
        # Находим заказ и проверяем, что он принадлежит текущему пользователю
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # Сохраняем информацию для сообщения
        order_id_val = order.id
        order_status = order.status

        # Дополнительная проверка: нельзя удалять доставленные заказы
        if order.status == "доставлен":
            messages.error(request, "Нельзя удалить доставленный заказ.")
            return redirect("orders:purchase_orders")

        # Создаем уведомления для мастеров перед удалением (если это не наш собственный товар)
        masters_notified = set()
        for item in order.items.all():
            master = item.product.master
            if master.id != request.user.id and master.id not in masters_notified:
                try:
                    # Уведомляем мастера об отмене заказа покупателем
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

        # Удаляем заказ
        order.delete()

        logger.info(
            "Order deleted by customer. Order ID: %s, User: %s",
            order_id_val,
            request.user.id,
        )

        messages.success(request, f"Заказ #{order_id_val} успешно удален.")

    except Order.DoesNotExist:
        logger.error(
            "Order not found for deletion. Order ID: %s, User: %s",
            order_id,
            request.user.id,
        )
        messages.error(request, "Заказ не найден или у вас нет прав для его удаления.")
    except Exception as e:
        logger.error(
            "Error deleting order %s by user %s: %s",
            order_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, f"Ошибка при удалении заказа: {str(e)}")

    return redirect("orders:purchase_orders")


@login_required
@transaction.atomic
def delete_sale_order(request, order_id):
    """
    Удаление заказа мастером с улучшенной логикой
    """
    try:
        # Получаем заказ
        order = get_object_or_404(Order, id=order_id)

        # Проверяем, что в заказе есть товары этого мастера
        master_items = order.items.filter(product__master=request.user)
        if not master_items.exists():
            messages.error(request, "Этот заказ не содержит ваших товаров.")
            return redirect("orders:sale_orders")

        # Уведомляем покупателя об отмене заказа мастером (если это не наш собственный заказ)
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

        messages.success(request, f"Заказ #{order_id_val} был успешно удален.")

    except Order.DoesNotExist:
        logger.error(
            "Sale order not found for deletion. Order ID: %s, User: %s",
            order_id,
            request.user.id,
        )
        messages.error(request, "Заказ не найден.")
    except Exception as e:
        logger.error(
            "Error deleting sale order %s by user %s: %s",
            order_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, f"При удалении заказа произошла ошибка: {str(e)}")

    return redirect("orders:sale_orders")

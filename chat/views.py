import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from notifications.services import NotificationService
from products.models import Product

from .models import Dialogue, Message

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
def dialogue_list(request):
    """Список диалогов пользователя с аннотацией непрочитанных сообщений"""
    try:
        # Ищем диалоги, где пользователь является user1 или user2
        dialogues = (
            Dialogue.objects.filter(Q(user1=request.user) | Q(user2=request.user))
            .annotate(
                unread_messages_count=Count(
                    "messages",
                    filter=Q(messages__is_read=False)
                    & ~Q(messages__sender=request.user),
                )
            )
            .order_by("-updated_at")
        )

        # Добавляем дополнительную информацию для каждого диалога
        dialogues_list = []
        for dialogue in dialogues:
            last_message = dialogue.messages.order_by("-created_at").first()
            messages_count = dialogue.messages.count()

            dialogues_list.append(
                {
                    "id": dialogue.id,
                    "other_user": dialogue.get_other_user(request.user),
                    "product": dialogue.product,
                    "last_message": last_message,
                    "messages_count": messages_count,
                    "unread_count": dialogue.unread_messages_count,
                    "created_at": dialogue.created_at,
                    "updated_at": dialogue.updated_at,
                }
            )

        return render(request, "chat/dialogue_list.html", {"dialogues": dialogues_list})

    except Exception as e:
        logger.error(
            "Error loading dialogue list for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при загрузке списка диалогов")
        return redirect("products:catalog")


@login_required
def dialogue_detail(request, pk):
    """Страница конкретного диалога"""
    try:
        dialogue = get_object_or_404(Dialogue, id=pk)

        # Проверка прав доступа - пользователь должен быть участником диалога
        if request.user not in [dialogue.user1, dialogue.user2]:
            messages.error(request, "У вас нет доступа к этому диалогу")
            return redirect("chat:dialogue_list")

        # Получаем собеседника
        interlocutor = dialogue.get_other_user(request.user)

        # Помечаем сообщения как прочитанные при заходе в диалог
        if request.method == "GET":
            # Помечаем все непрочитанные сообщения от собеседника как прочитанные
            Message.objects.filter(dialogue=dialogue, is_read=False).exclude(
                sender=request.user
            ).update(is_read=True)

            # Помечаем уведомления о сообщениях в этом диалоге как прочитанные
            NotificationService.mark_dialogue_notifications_read(request.user, pk)

        # Обработка отправки нового сообщения
        if request.method == "POST":
            text = request.POST.get("message", "").strip()
            if text:
                message = Message.objects.create(
                    dialogue=dialogue, sender=request.user, text=text
                )

                # Создаем уведомление для собеседника
                NotificationService.create_message_notification(
                    sender=request.user,
                    recipient=interlocutor,
                    message_text=text,
                    dialogue_id=pk,
                )

                messages.success(request, "Сообщение отправлено")
                return redirect("chat:dialogue_detail", pk=pk)

        # Получаем все сообщения диалога
        messages_list = dialogue.messages.order_by("created_at")

        return render(
            request,
            "chat/dialogue_detail.html",
            {
                "dialogue": dialogue,
                "interlocutor": interlocutor,
                "messages": messages_list,
            },
        )

    except Exception as e:
        logger.error(
            "Error in dialogue detail for dialogue %s, user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при загрузке диалога")
        return redirect("chat:dialogue_list")


@login_required
@require_POST
def send_message(request, pk):
    """API endpoint для отправки сообщения"""
    try:
        dialogue = get_object_or_404(Dialogue, id=pk)

        # Проверка прав доступа
        if request.user not in [dialogue.user1, dialogue.user2]:
            logger.error(
                "User %s attempted to send message to unauthorized dialogue %s",
                request.user.id,
                pk,
            )
            return JsonResponse({"status": "error", "message": "No permission"})

        text = request.POST.get("text", "").strip()
        if text:
            message = Message.objects.create(
                dialogue=dialogue, sender=request.user, text=text
            )

            # Получаем собеседника
            interlocutor = dialogue.get_other_user(request.user)

            # Создаем уведомление для собеседника
            NotificationService.create_message_notification(
                sender=request.user,
                recipient=interlocutor,
                message_text=text,
                dialogue_id=pk,
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message_id": message.id,
                    "created_at": message.created_at.strftime("%d.%m.%Y %H:%M"),
                }
            )

        return JsonResponse({"status": "error", "message": "Empty message"})

    except Exception as e:
        logger.error(
            "Error sending message in dialogue %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"status": "error", "message": "Internal server error"})


@login_required
@require_POST
def mark_messages_read(request, pk):
    """API endpoint для пометки сообщений как прочитанных"""
    try:
        dialogue = get_object_or_404(Dialogue, id=pk)

        # Проверка прав доступа
        if request.user not in [dialogue.user1, dialogue.user2]:
            logger.error(
                "User %s attempted to mark messages read in unauthorized dialogue %s",
                request.user.id,
                pk,
            )
            return JsonResponse({"status": "error", "message": "No permission"})

        # Помечаем все сообщения собеседника как прочитанные
        messages_to_mark = Message.objects.filter(
            dialogue=dialogue, is_read=False
        ).exclude(sender=request.user)

        updated_count = messages_to_mark.update(is_read=True)

        # Помечаем уведомления как прочитанные
        NotificationService.mark_dialogue_notifications_read(request.user, pk)

        return JsonResponse({"status": "success", "updated_count": updated_count})

    except Exception as e:
        logger.error(
            "Error marking messages read in dialogue %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"status": "error", "message": "Internal server error"})


@login_required
def delete_dialogue(request, pk):
    """Удаление диалога"""
    try:
        dialogue = get_object_or_404(Dialogue, id=pk)

        # Проверяем права доступа
        if request.user not in [dialogue.user1, dialogue.user2]:
            messages.error(request, "У вас нет прав для удаления этого диалога")
            return redirect("chat:dialogue_list")

        if request.method == "POST":
            # Удаляем уведомления о диалоге для обоих пользователей
            NotificationService.delete_dialogue_notifications(dialogue.user1, pk)
            NotificationService.delete_dialogue_notifications(dialogue.user2, pk)

            # Полное удаление диалога и всех сообщений
            dialogue.messages.all().delete()
            dialogue.delete()

            messages.success(request, "Диалог успешно удален")
            return redirect("chat:dialogue_list")

        return redirect("chat:dialogue_list")

    except Exception as e:
        logger.error(
            "Error deleting dialogue %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении диалога")
        return redirect("chat:dialogue_list")


@login_required
def clear_all_dialogues(request):
    """Удаление всех диалогов пользователя"""
    try:
        if request.method == "POST":
            # Находим все диалоги пользователя
            dialogues = Dialogue.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            )

            deleted_count = dialogues.count()

            # Удаляем все сообщения, диалоги и уведомления
            for dialogue in dialogues:
                NotificationService.delete_dialogue_notifications(
                    dialogue.user1, dialogue.id
                )
                NotificationService.delete_dialogue_notifications(
                    dialogue.user2, dialogue.id
                )
                dialogue.messages.all().delete()
                dialogue.delete()

            messages.success(request, f"Удалено {deleted_count} диалогов")
            return redirect("chat:dialogue_list")

        return redirect("chat:dialogue_list")

    except Exception as e:
        logger.error(
            "Error clearing all dialogues for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении диалогов")
        return redirect("chat:dialogue_list")


@login_required
def start_dialogue_from_product(request, pk):
    """Начать диалог из карточки товара"""
    try:
        product = get_object_or_404(Product, id=pk)

        # Проверяем, что пользователь не пытается написать сам себе
        if request.user == product.master:
            messages.error(request, "Вы не можете начать диалог с самим собой")
            return redirect("products:product_detail", pk=pk)

        # Ищем существующий диалог для этого товара
        dialogue = Dialogue.objects.filter(
            product=product, user1=request.user, user2=product.master
        ).first()

        if not dialogue:
            # Пробуем в обратном порядке пользователей
            dialogue = Dialogue.objects.filter(
                product=product, user1=product.master, user2=request.user
            ).first()

        # Создаем новый диалог если не нашли
        if not dialogue:
            dialogue = Dialogue.objects.create(
                user1=request.user, user2=product.master, product=product
            )

        return redirect("chat:dialogue_detail", pk=dialogue.id)

    except Exception as e:
        logger.error(
            "Error starting dialogue from product %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при создании диалога")
        return redirect("products:product_detail", pk=pk)

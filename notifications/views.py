import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)


@login_required
def notification_list(request):
    """Список всех уведомлений"""
    try:
        notifications = Notification.objects.filter(user=request.user)

        # Помечаем как прочитанные при просмотре полного списка
        if request.GET.get("mark_read"):
            NotificationService.mark_all_as_read(request.user)

        context = {"notifications": notifications, "active_tab": "notifications"}
        return render(request, "notifications/notification_list.html", context)

    except Exception as e:
        logger.error(
            "Error loading notification list for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при загрузке уведомлений")
        return redirect("products:catalog")


@login_required
@require_GET
def unread_count_api(request):
    """API для получения количества непрочитанных уведомлений"""
    try:
        count = NotificationService.get_unread_count(request.user)
        return JsonResponse({"count": count})

    except Exception as e:
        logger.error(
            "Error getting unread count for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"count": 0})


@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Пометить уведомление как прочитанное"""
    try:
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user
        )
        notification.mark_as_read()
        return JsonResponse({"success": True})

    except Exception as e:
        logger.error(
            "Error marking notification %s as read for user %s: %s",
            notification_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"success": False})


@login_required
@require_POST
def mark_all_read(request):
    """Пометить все уведомления как прочитанные"""
    try:
        NotificationService.mark_all_as_read(request.user)
        return JsonResponse({"success": True})

    except Exception as e:
        logger.error(
            "Error marking all notifications as read for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"success": False})


@login_required
@require_POST
def delete_notification(request, notification_id):
    """Удалить одно прочитанное уведомление"""
    try:
        success = NotificationService.delete_single_notification(
            request.user, notification_id
        )
        return JsonResponse({"success": success})

    except Exception as e:
        logger.error(
            "Error deleting notification %s for user %s: %s",
            notification_id,
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"success": False})


@login_required
@require_POST
def delete_all_read(request):
    """Удалить все прочитанные уведомления"""
    try:
        deleted_count = NotificationService.delete_read_notifications(request.user)
        return JsonResponse({"success": True, "deleted_count": deleted_count})

    except Exception as e:
        logger.error(
            "Error deleting all read notifications for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        return JsonResponse({"success": False, "deleted_count": 0})

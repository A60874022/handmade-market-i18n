# notifications/context_processors.py
from django.db.models import Count, Q

from chat.models import Dialogue

from .models import Notification


def notifications_context(request):
    """Добавляет уведомления в контекст всех шаблонов"""
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user, is_read=False
        ).order_by("-created_at")[
            :5
        ]  # Последние 5 непрочитанных

        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return {
            "unread_notifications": unread_notifications,
            "unread_notifications_count": unread_count,
        }
    return {}


def chat_context(request):
    """Добавляет информацию о чате в контекст всех шаблонов"""
    if request.user.is_authenticated:
        # Подсчет всех непрочитанных сообщений
        total_unread_messages = (
            Dialogue.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).aggregate(
                total_unread=Count(
                    "messages",
                    filter=Q(messages__is_read=False)
                    & ~Q(messages__sender=request.user),
                )
            )[
                "total_unread"
            ]
            or 0
        )

        return {
            "total_unread_messages": total_unread_messages,
        }
    return {}

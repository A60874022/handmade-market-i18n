from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("new_order", _("🎉 New order")),
        ("order_status_changed", _("📦 Order status changed")),
        ("new_message", _("💬 New message")),
        ("product_favorited", _("❤️ Product added to favorites")),
        ("system", _("🔔 System notification")),
        ("order_cancelled", _("❌ Order cancelled")),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="notifications",
        verbose_name=_("user")
    )
    notification_type = models.CharField(
        max_length=50, 
        choices=NOTIFICATION_TYPES,
        verbose_name=_("notification type")
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_("title")
    )
    message = models.TextField(
        verbose_name=_("message")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("is read")
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("created at")
    )

    # Links to related objects
    related_object_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name=_("related object ID")
    )
    related_content_type = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_("related content type")
    )
    action_url = models.CharField(
        max_length=500, 
        blank=True,
        verbose_name=_("action URL")
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
        ]
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")

    def __str__(self):
        return _("%(type)s for %(email)s") % {
            "type": self.get_notification_type_display(),
            "email": self.user.email,
        }

    def mark_as_read(self):
        self.is_read = True
        self.save()

    @property
    def is_recent(self):
        return (timezone.now() - self.created_at).days < 1

    def can_delete(self):
        """Only read notifications can be deleted"""
        return self.is_read
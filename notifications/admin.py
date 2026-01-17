from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__email", "title", "message"]
    readonly_fields = ["created_at"]
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        (_('Status'), {
            'fields': ('is_read', 'created_at')
        }),
        (_('Related objects'), {
            'fields': ('related_object_id', 'related_content_type', 'action_url'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = _('User email')
    user_email.admin_order_field = 'user__email'
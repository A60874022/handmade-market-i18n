# chat/admin.py
from django.contrib import admin

from .models import Dialogue, Message





@admin.register(Dialogue)
class DialogueAdmin(admin.ModelAdmin):
    list_display = ["id", "user1", "user2", "product", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["user1__email", "user2__email", "product__name"]
    raw_id_fields = ["user1", "user2", "product"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        ("Участники диалога", {"fields": ["user1", "user2"]}),
        ("Продукт", {"fields": ["product"], "classes": ["collapse"]}),
        ("Даты", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "dialogue", "sender", "text_preview", "created_at", "is_read"]
    list_filter = ["created_at", "is_read"]
    search_fields = ["text", "sender__email", "dialogue__id"]
    raw_id_fields = ["dialogue", "sender"]
    list_select_related = ["dialogue", "sender"]
    readonly_fields = ["created_at"]

    fieldsets = [
        ("Основная информация", {"fields": ["dialogue", "sender", "is_read"]}),
        ("Сообщение", {"fields": ["text"]}),
        ("Дата", {"fields": ["created_at"], "classes": ["collapse"]}),
    ]

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    text_preview.short_description = "Текст (превью)"

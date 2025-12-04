from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Dialogue(models.Model):
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="dialogues_as_user1"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="dialogues_as_user2"
    )
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["user1", "user2", "product"]

    def __str__(self):
        return f"Чат по товару '{self.product.title}' между {self.user1.email} и {self.user2.email}"

    def get_other_user(self, current_user):
        """Возвращает собеседника текущего пользователя"""
        if current_user == self.user1:
            return self.user2
        elif current_user == self.user2:
            return self.user1
        return None

    def get_unread_count(self, user):
        """Подсчитывает непрочитанные сообщения от собеседника"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    @property
    def master(self):
        """Владелец товара (продавец)"""
        return self.product.master

    @property
    def customer(self):
        """Покупатель (второй участник диалога)"""
        if self.user1 == self.product.master:
            return self.user2
        else:
            return self.user1


class Message(models.Model):
    dialogue = models.ForeignKey(
        Dialogue, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_messages"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Сообщение от {self.sender.email}: {self.text[:50]}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()

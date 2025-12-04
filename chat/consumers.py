import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Dialogue, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Вызывается при установке соединения"""
        try:
            self.dialogue_id = self.scope["url_route"]["kwargs"]["dialogue_id"]
            self.room_group_name = f"chat_{self.dialogue_id}"
            self.user = self.scope["user"]

            # Проверяем авторизацию и доступ к диалогу
            if self.user.is_anonymous:
                await self.close(code=4001)
                return

            if not await self.has_dialogue_access():
                await self.close(code=4003)
                return

            # Присоединяемся к группе комнаты
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Помечаем сообщения как прочитанные при подключении
            await self.mark_messages_as_read()

        except KeyError as e:
            print(f"KeyError in connect: {e}")
            await self.close(code=4000)
        except Exception as e:
            print(f"Error in connect: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Вызывается при разрыве соединения"""
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        """Вызывается при получении сообщения от клиента"""
        try:
            text_data_json = json.loads(text_data)
            message_text = text_data_json.get("message")

            if not message_text:
                await self.send(json.dumps({"error": "Empty message"}))
                return

            # Используем текущего пользователя как отправителя
            sender_id = self.user.id

            # Сохраняем сообщение в БД
            message_obj = await self.save_message(message_text, sender_id)

            if message_obj:
                # Получаем собеседника для определения, кому показывать уведомления
                interlocutor = await self.get_interlocutor()

                # Отправляем сообщение всем в группе
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message_text,
                        "sender_id": sender_id,
                        "sender_email": self.user.email,
                        "timestamp": message_obj.created_at.isoformat(),
                        "message_id": message_obj.id,
                        "interlocutor_id": interlocutor.id if interlocutor else None,
                    },
                )
            else:
                await self.send(json.dumps({"error": "Failed to save message"}))

        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            print(f"Error in receive: {e}")
            await self.send(json.dumps({"error": "Server error"}))

    async def chat_message(self, event):
        """Отправляет сообщение вебсокету"""
        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "message": event["message"],
                        "sender_id": event["sender_id"],
                        "sender_email": event["sender_email"],
                        "timestamp": event["timestamp"],
                        "message_id": event["message_id"],
                        "is_own_message": event["sender_id"] == self.user.id,
                    }
                )
            )
        except Exception as e:
            print(f"Error in chat_message: {e}")

    @database_sync_to_async
    def has_dialogue_access(self):
        """Проверяет, имеет ли пользователь доступ к диалогу"""
        try:
            dialogue = Dialogue.objects.get(id=self.dialogue_id)
            # ОБНОВЛЕНО: Проверка для универсальных пользователей
            return self.user in [dialogue.user1, dialogue.user2]
        except Dialogue.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message_text, sender_id):
        """Сохраняет сообщение в базу данных"""
        try:
            dialogue = Dialogue.objects.get(id=self.dialogue_id)
            sender = User.objects.get(id=sender_id)

            message = Message.objects.create(
                dialogue=dialogue, sender=sender, text=message_text
            )

            # Обновляем время последнего обновления диалога
            dialogue.save()

            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def mark_messages_as_read(self):
        """Помечает все сообщения собеседника как прочитанные"""
        try:
            dialogue = Dialogue.objects.get(id=self.dialogue_id)
            # Помечаем сообщения собеседника как прочитанные
            Message.objects.filter(dialogue=dialogue, is_read=False).exclude(
                sender=self.user
            ).update(is_read=True)
        except Exception as e:
            print(f"Error marking messages as read: {e}")

    @database_sync_to_async
    def get_interlocutor(self):
        """Возвращает собеседника текущего пользователя"""
        try:
            dialogue = Dialogue.objects.get(id=self.dialogue_id)
            return dialogue.get_other_user(self.user)
        except Dialogue.DoesNotExist:
            return None

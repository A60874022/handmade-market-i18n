"""
Сервисный модуль для отправки email сообщений.

Обеспечивает централизованное управление отправкой email, обработку ошибок
и единообразное форматирование сообщений.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class EmailService:
    """
    Сервис для отправки email сообщений.

    Предоставляет методы для отправки различных типов email:
    - верификация email через код
    - уведомления
    - транзакционные сообщения
    """

    @staticmethod
    def send_verification_code_email(
        user_email: str,
        verification_code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Отправляет email с кодом для подтверждения адреса.

        Args:
            user_email: Email адрес получателя
            verification_code: 6-значный код подтверждения
            context: Дополнительный контекст для шаблона

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        try:
            # Подготавливаем контекст для шаблона
            email_context = {
                "verification_code": verification_code,
                "user_email": user_email,
                "site_name": getattr(settings, "SITE_NAME", "Handmade Marketplace"),
                "support_email": getattr(
                    settings, "SUPPORT_EMAIL", "support@example.com"
                ),
                **(context or {}),
            }

            # Рендерим HTML версию письма
            subject = _("Код подтверждения email")
            html_message = render_to_string(
                "users/emails/email_verification_code.html",  # Исправленный путь
                email_context,
            )
            text_message = strip_tags(html_message)

            # Отправляем email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
                reply_to=[getattr(settings, "SUPPORT_EMAIL", "support@example.com")],
            )
            email.attach_alternative(html_message, "text/html")

            sent_count = email.send(fail_silently=False)

            logger.info(
                f"Verification code email sent to {user_email}. "
                f"Sent count: {sent_count}"
            )

            return sent_count > 0

        except Exception as e:
            logger.error(
                f"Failed to send verification code email to {user_email}. "
                f"Error: {str(e)}",
                exc_info=True,
            )
            return False

    @staticmethod
    def send_welcome_email(user_email: str, user_name: str = None) -> bool:
        """
        Отправляет приветственное письмо после успешной регистрации и подтверждения email.

        Args:
            user_email: Email адрес получателя
            user_name: Имя пользователя (опционально)

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        try:
            context = {
                "user_email": user_email,
                "user_name": user_name,
                "site_name": getattr(settings, "SITE_NAME", "Handmade Marketplace"),
                "support_email": getattr(
                    settings, "SUPPORT_EMAIL", "support@example.com"
                ),
            }

            subject = _("Добро пожаловать в Handmade Marketplace!")
            html_message = render_to_string("users/emails/welcome_email.html", context)
            text_message = strip_tags(html_message)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
            )
            email.attach_alternative(html_message, "text/html")

            sent_count = email.send(fail_silently=False)

            logger.info(f"Welcome email sent to {user_email}. Sent count: {sent_count}")
            return sent_count > 0

        except Exception as e:
            logger.error(
                f"Failed to send welcome email to {user_email}. Error: {str(e)}"
            )
            return False

    @staticmethod
    def send_password_reset_email(
        user_email: str, reset_url: str, user_name: str = None
    ) -> bool:
        """
        Отправляет письмо для сброса пароля.

        Args:
            user_email: Email адрес получателя
            reset_url: URL для сброса пароля
            user_name: Имя пользователя (опционально)

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        try:
            context = {
                "reset_url": reset_url,
                "user_email": user_email,
                "user_name": user_name,
                "site_name": getattr(settings, "SITE_NAME", "Handmade Marketplace"),
                "support_email": getattr(
                    settings, "SUPPORT_EMAIL", "support@example.com"
                ),
            }

            subject = _("Сброс пароля")
            html_message = render_to_string("users/emails/password_reset.html", context)
            text_message = strip_tags(html_message)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
            )
            email.attach_alternative(html_message, "text/html")

            sent_count = email.send(fail_silently=False)

            logger.info(
                f"Password reset email sent to {user_email}. Sent count: {sent_count}"
            )
            return sent_count > 0

        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {user_email}. Error: {str(e)}"
            )
            return False

    @staticmethod
    def send_notification(
        user_email: str, subject: str, template_name: str, context: Dict[str, Any]
    ) -> bool:
        """
        Универсальный метод для отправки уведомлений.

        Args:
            user_email: Email адрес получателя
            subject: Тема письма
            template_name: Имя шаблона (без расширения)
            context: Контекст для шаблона

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        try:
            base_context = {
                "site_name": getattr(settings, "SITE_NAME", "Handmade Marketplace"),
                "support_email": getattr(
                    settings, "SUPPORT_EMAIL", "support@example.com"
                ),
            }
            context = {**base_context, **context}

            html_message = render_to_string(f"{template_name}.html", context)
            text_message = strip_tags(html_message)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
            )
            email.attach_alternative(html_message, "text/html")

            sent_count = email.send(fail_silently=False)

            logger.info(
                f"Notification '{subject}' sent to {user_email}. Sent count: {sent_count}"
            )
            return sent_count > 0

        except Exception as e:
            logger.error(
                f"Failed to send notification to {user_email}. "
                f"Subject: {subject}. Error: {str(e)}"
            )
            return False

    def send_product_approved_email(
        self, user_email, product_title, product_url, context=None
    ):
        """
        Отправляет письмо об одобрении товара
        """
        try:
            if context is None:
                context = {}

            # Если URL относительный, делаем его абсолютным
            if product_url.startswith("/"):
                site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
                product_url = site_url + product_url

            context.update(
                {
                    "product_title": product_title,
                    "product_url": product_url,
                    "site_name": "HandmadeMarket",
                }
            )

            subject = f'Ваш товар "{product_title}" одобрен!'

            html_message = f"""
            <h1>Ваш товар одобрен!</h1>
            <p>Здравствуйте!</p>
            <p>Мы рады сообщить, что ваш товар <strong>"{product_title}"</strong> был успешно одобрен.</p>
            <p><a href="{product_url}">Посмотреть товар</a></p>
            """

            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Product approved email sent to {user_email}")
            return True

        except Exception as e:
            logger.error(
                f"Error sending product approved email to {user_email}: {str(e)}"
            )
            return False


# Создаем экземпляр сервиса для удобного импорта
email_service = EmailService()

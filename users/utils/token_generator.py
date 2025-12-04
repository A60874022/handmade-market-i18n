"""
Утилиты для генерации и валидации токенов безопасности.

Обеспечивает криптографически безопасную генерацию токенов
для различных целей (верификация email, сброс пароля и т.д.).
"""

import secrets
import string
from datetime import timedelta
from typing import Optional

from django.utils import timezone


class TokenGenerator:
    """
    Генератор безопасных токенов для различных целей.

    Предоставляет методы для создания и проверки токенов
    с настраиваемой длиной и сроком действия.
    """

    @staticmethod
    def generate_verification_token(length: int = 32) -> str:
        """
        Генерирует криптографически безопасный токен для верификации.

        Args:
            length: Длина токена в байтах (по умолчанию 32)

        Returns:
            str: Сгенерированный токен в формате URL-safe base64
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_numeric_code(length: int = 6) -> str:
        """
        Генерирует числовой код для SMS или быстрой верификации.

        Args:
            length: Длина числового кода

        Returns:
            str: Строка, содержащая только цифры
        """
        if length < 4:
            raise ValueError("Code length must be at least 4 digits")

        digits = string.digits
        return "".join(secrets.choice(digits) for _ in range(length))

    @staticmethod
    def is_token_valid(created_at: timezone.datetime, expiry_hours: int = 24) -> bool:
        """
        Проверяет, не истек ли срок действия токена.

        Args:
            created_at: Время создания токена
            expiry_hours: Срок действия в часах

        Returns:
            bool: True если токен действителен, False если истек
        """
        if not created_at:
            return False

        expiry_time = created_at + timedelta(hours=expiry_hours)
        return timezone.now() <= expiry_time


# Создаем экземпляр генератора для удобного импорта
token_generator = TokenGenerator()

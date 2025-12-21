# ad_service/middleware.py

from django.conf import settings
from django.utils import translation


class LanguageDetectionMiddleware:
    """
    Middleware для определения языка из заголовков браузера
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Если язык уже установлен в сессии или куках - используем его
        if hasattr(request, "session") and "django_language" in request.session:
            language = request.session["django_language"]
        elif "django_language" in request.COOKIES:
            language = request.COOKIES["django_language"]
        else:
            # Определяем язык из заголовка Accept-Language браузера
            language = self.get_browser_language(request)

            # Сохраняем в сессии для будущих запросов
            if hasattr(request, "session"):
                request.session["django_language"] = language
            request.META["HTTP_ACCEPT_LANGUAGE"] = language

        # Активируем язык
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        # Устанавливаем заголовки Content-Language
        response["Content-Language"] = language

        return response

    def get_browser_language(self, request):
        """
        Извлекает язык из заголовка Accept-Language браузера
        и возвращает один из поддерживаемых языков
        """
        accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")

        # Парсим заголовок Accept-Language
        languages = []
        if accept_language:
            # Пример: "fr-CH, fr;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5"
            parts = accept_language.split(",")
            for part in parts:
                lang = part.split(";")[0].strip()
                if lang and "-" in lang:
                    lang = lang.split("-")[0]  # Берем основную часть (fr-CH -> fr)
                if lang:
                    languages.append(lang)

        # Проверяем каждый язык из заголовка, поддерживаем ли мы его
        for lang in languages:
            if lang in dict(settings.LANGUAGES):
                return lang

        # Если не нашли подходящий - возвращаем английский по умолчанию
        return settings.LANGUAGE_CODE

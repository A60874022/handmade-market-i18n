# ad_service/context_processors.py

from django.conf import settings
from django.utils import translation


def language_context(request):
    """
    Добавляет информацию о языке в контекст шаблонов
    """
    return {
        "LANGUAGES": settings.LANGUAGES,
        "CURRENT_LANGUAGE": translation.get_language(),
        "CURRENT_LANGUAGE_NAME": dict(settings.LANGUAGES).get(
            translation.get_language(), "English"
        ),
    }

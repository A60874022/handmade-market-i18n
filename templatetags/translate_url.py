# ad_service/templatetags/translate_url.py
from django import template
from django.urls import translate_url as django_translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def translate_url(context, lang_code):
    path = context["request"].path
    return django_translate_url(path, lang_code)

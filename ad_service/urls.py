from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import set_language

# URL-паттерны БЕЗ префикса языка
urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/setlang/", set_language, name="set_language"),
    # Главная страница без префикса языка
    path("", RedirectView.as_view(pattern_name="products:catalog"), name="home"),
]

# Добавляем Rosetta только в режиме разработки
if settings.DEBUG:
    from rosetta.urls import urlpatterns as rosetta_urls

    urlpatterns += [path("rosetta/", include(rosetta_urls))]

# URL-паттерны С префиксом языка (для каталога, заказов и т.д.)
urlpatterns += i18n_patterns(
    # Приложения с поддержкой языка
    path("catalog/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("users/", include("users.urls")),
    path("chat/", include("chat.urls")),
    path("notifications/", include("notifications.urls")),
    path("", include("pages.urls")),  # Эта строка должна быть ПОСЛЕДНЕЙ
    prefix_default_language=True,
)

# Статические и медиа файлы
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

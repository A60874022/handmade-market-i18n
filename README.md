

Рабочая версия сайта Marketplace с поддержкой нескольких языков (i18n).

## Требования

- Docker >= 24
- Docker Compose >= 2
- Python 3.11 (локально, если нужно)
- Node.js/NPM (для сборки фронтенда, если используете static assets)

---

## Структура проекта

```

handmade-market-i18n/
├─ backend/          # Django проект
├─ locale/           # Переводы
├─ static/           # Статические файлы
├─ templates/        # Django templates
├─ tests/            # Папка для тестов (pytest)
├─ Dockerfile
├─ docker-compose.yml
└─ README.md

````

---

## Быстрый запуск через Docker

1. Клонируем репозиторий:

```bash
git clone https://github.com/A60874022/handmade-market-i18n.git
cd handmade-market-i18n
````

2. Создаем `.env` (пример):

```env
DEBUG=True
SECRET_KEY=changeme
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]
POSTGRES_DB=handmade
POSTGRES_USER=handmade
POSTGRES_PASSWORD=handmade
POSTGRES_HOST=db
POSTGRES_PORT=5432
LANGUAGE_CODE=fr
TIME_ZONE=Europe/Paris
```

3. Собираем и запускаем контейнеры:

```bash
docker compose up --build
```

4. Применяем миграции:

```bash
docker compose exec web python manage.py migrate
```

5. Создаем суперпользователя (для админки):

```bash
docker compose exec web python manage.py createsuperuser
```

6. Компилируем переводы (i18n):

```bash
docker compose exec web python manage.py compilemessages
```

7. Открываем сайт в браузере:

```
http://localhost:8000/
```

---

## Работа с тестами

Тесты находятся в папке `tests/`.
Чтобы запустить:

```bash
docker compose exec web pytest tests/
```


## Админка

* URL: `/admin/`
* Используйте суперпользователя, созданного выше.

---

## Локализация

* Переводы хранятся в папке `locale/`
* Команды для работы с переводами:

```bash
# Создание новых сообщений для перевода
docker compose exec web python manage.py makemessages -l fr

# Компиляция сообщений
docker compose exec web python manage.py compilemessages

* Статические файлы собираются через стандарт Django `collectstatic`:

```bash
docker compose exec web python manage.py collectstatic --noinput
```

* Для продакшн:

  * установить `DEBUG=False`
  * задать реальные `SECRET_KEY` и `ALLOWED_HOSTS`
  * подключить HTTPS через reverse proxy (nginx, Traefik или другой)


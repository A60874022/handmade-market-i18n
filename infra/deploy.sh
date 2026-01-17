#!/bin/bash

# deploy.sh - Скрипт автоматического деплоя Django приложения с SSL

set -e  # Остановить скрипт при любой ошибке

echo "🚀 Начинаем процесс деплоя..."
echo "========================================"

# Переходим в директорию проекта
cd /root/ad_service/infra

# 1. Останавливаем существующие контейнеры (если есть)
echo "1. Останавливаем старые контейнеры..."
docker-compose down --remove-orphans || true

# 2. Подтягиваем последние образы
echo "2. Подтягиваем последние Docker образы..."
docker-compose pull

# 3. Запускаем базу данных, Redis и Django (без nginx)
echo "3. Запускаем базу данных, Redis и Django..."
docker-compose up -d db redis web

# 4. Ждем запуска Django
echo "4. Ждем запуска Django (30 секунд)..."
sleep 30

# 5. Проверяем, запустился ли Django
if docker-compose ps web | grep -q "Up"; then
    echo "✅ Django успешно запущен"
else
    echo "❌ Django не запустился. Проверяем логи..."
    docker-compose logs web
    exit 1
fi

# 6. Проверяем, есть ли уже SSL сертификаты
CERT_PATH="./certbot/conf/live/mart.akatosphere.com/fullchain.pem"
if [ -f "$CERT_PATH" ]; then
    echo "6. SSL сертификаты уже существуют, используем SSL конфиг"
    cp ./nginx/conf.d/django-ssl.conf ./nginx/conf.d/default.conf
else
    echo "6. SSL сертификатов нет, используем HTTP конфиг для их получения"
    cp ./nginx/conf.d/django.conf ./nginx/conf.d/default.conf
fi

# 7. Запускаем nginx
echo "7. Запускаем nginx..."
docker-compose up -d nginx

# 8. Если нет сертификатов - получаем их
if [ ! -f "$CERT_PATH" ]; then
    echo "8. Получаем SSL сертификаты..."
    
    # Создаем необходимые директории
    mkdir -p ./certbot/www ./certbot/conf
    
    # Запускаем certbot для получения сертификатов
    docker run --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot --webroot-path=/var/www/certbot \
        --email "$CERTBOT_EMAIL" \
        --agree-tos --no-eff-email \
        -d "mart.akatosphere.com" \
        -d "www.mart.akatosphere.com" \
        --force-renewal || echo "⚠️ Не удалось получить сертификаты, проверьте настройки домена"
    
    # Если сертификаты получены - переключаем на SSL конфиг
    if [ -f "$CERT_PATH" ]; then
        echo "✅ Сертификаты получены, переключаем на SSL"
        cp ./nginx/conf.d/django-ssl.conf ./nginx/conf.d/default.conf
        docker-compose restart nginx
        
        # Настраиваем автообновление сертификатов
        echo "9. Настраиваем автообновление сертификатов..."
        echo "0 12 * * * docker run --rm \
            -v /root/ad_service/infra/certbot/conf:/etc/letsencrypt \
            -v /root/ad_service/infra/certbot/www:/var/www/certbot \
            certbot/certbot renew --quiet && \
            docker-compose -f /root/ad_service/infra/docker-compose.yml restart nginx" \
            | crontab -
    else
        echo "⚠️ Сайт будет работать по HTTP. Для получения SSL:"
        echo "   - Убедитесь что домен mart.akatosphere.com указывает на IP сервера"
        echo "   - Убедитесь что порт 80 открыт в фаерволе"
    fi
fi

# 9. Проверяем статус всех сервисов
echo "========================================"
echo "📊 Статус сервисов:"
docker-compose ps

# 10. Показываем логи nginx для проверки
echo "========================================"
echo "📝 Последние логи nginx:"
docker-compose logs nginx --tail=20

echo "========================================"
echo "🎉 Деплой завершен!"
echo "🌐 Сайт доступен по адресу: https://mart.akatosphere.com"
echo "🔧 Для проверки конфигурации nginx: docker-compose exec nginx nginx -t"
echo "📋 Для просмотра логов: docker-compose logs -f"
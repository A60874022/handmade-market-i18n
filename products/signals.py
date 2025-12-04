import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.urls import reverse
from django.http import HttpRequest
from .models import Product

logger = logging.getLogger(__name__)

# Словарь для хранения старых состояний
_old_states = {}


@receiver(pre_save, sender=Product)
def store_old_state(sender, instance, **kwargs):
    """
    Сохраняем старое состояние товара перед сохранением
    """
    if instance.pk:
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            # Сохраняем старое состояние в памяти
            _old_states[instance.pk] = {
                "is_approved": old_instance.is_approved,
                "is_active": old_instance.is_active,
            }
            print(
                f"📝 PRE-SAVE: Stored old state for product {instance.pk}: approved={old_instance.is_approved}"
            )
        except Product.DoesNotExist:
            print(f"📝 PRE-SAVE: New product {instance.pk} being created")
            _old_states[instance.pk] = None


@receiver(post_save, sender=Product)
def send_product_approval_email(sender, instance, created, **kwargs):
    """
    Сигнал для отправки email при одобрении товара
    """
    print(
        f"📦 POST-SAVE: Product {instance.pk}, Created: {created}, Approved: {instance.is_approved}"
    )

    # Если это создание нового товара
    if created:
        print("🆕 New product created")
        return

    # Получаем старое состояние из памяти
    old_state = _old_states.get(instance.pk)

    if old_state is None:
        print(f"⚠️ No old state found for product {instance.pk}")
        return

    old_approved = old_state.get("is_approved")
    new_approved = instance.is_approved

    print(f"🔄 Comparing: Old approval: {old_approved}, New approval: {new_approved}")

    # Проверяем, изменился ли статус одобрения с False на True
    if old_approved is False and new_approved is True:
        print("🎉 PRODUCT APPROVED! Sending email...")

        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from users.services.email_service import email_service

            # Формируем абсолютный URL товара
            # Способ 1: Используем SITE_URL из настроек, если он есть
            try:
                site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
                product_url = site_url + reverse(
                    "products:product_detail", kwargs={"pk": instance.pk}
                )
            except AttributeError:
                # Способ 2: Используем относительный URL
                product_url = reverse(
                    "products:product_detail", kwargs={"pk": instance.pk}
                )
                print(f"⚠️ SITE_URL not set, using relative URL: {product_url}")

            print(f"🔗 Product URL: {product_url}")

            # Отправляем email
            email_sent = email_service.send_product_approved_email(
                user_email=instance.master.email,
                product_title=instance.title,
                product_url=product_url,
                context={
                    "user_name": instance.master.get_short_name(),
                },
            )

            if email_sent:
                print(
                    f"✅ Approval email sent for product {instance.pk} to {instance.master.email}"
                )
                logger.info(
                    f"Product approval email sent successfully for product {instance.pk} to {instance.master.email}"
                )
            else:
                print(f"❌ Failed to send approval email for product {instance.pk}")
                logger.error(
                    f"Failed to send product approval email for product {instance.pk}"
                )

        except Exception as e:
            print(f"💥 Error sending email: {str(e)}")
            logger.error(
                f"Error sending approval email for product {instance.pk}: {str(e)}"
            )

    else:
        print("ℹ️ Approval status didn't change from False to True, skipping email")

    # Очищаем старое состояние
    if instance.pk in _old_states:
        del _old_states[instance.pk]

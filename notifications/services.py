from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import gettext as _

from .models import Notification


class NotificationService:

    @staticmethod
    def create_order_notification(order, master):
        """Create new order notification for master"""
        try:
            # Get this master's products in order
            master_items = order.items.filter(product__master=master)
            item_titles = ", ".join([item.product.title for item in master_items[:3]])

            if master_items.count() > 3:
                item_titles += _(" and %(count)d more products") % {
                    "count": master_items.count() - 3
                }

            total_for_master = sum(item.total_price for item in master_items)

            from orders.models import Order

            order_content_type = ContentType.objects.get_for_model(Order)

            Notification.objects.create(
                user=master,
                notification_type="new_order",
                title=_("🎉 New order!"),
                message=_(
                    "Customer %(email)s placed an order for your products: %(items)s. Total amount: %(total)s euros"
                )
                % {
                    "email": order.customer.email,
                    "items": item_titles,
                    "total": total_for_master,
                },
                action_url=f"/orders/sales/",
                related_object_id=order.id,
                related_content_type=order_content_type,
            )
            return True
        except Exception as e:
            print(f"Error creating notification: {e}")
            return False

    @staticmethod
    def create_message_notification(sender, recipient, message_text, dialogue_id):
        """Create new message notification"""
        try:
            from chat.models import Dialogue

            dialogue_content_type = ContentType.objects.get_for_model(Dialogue)

            # Check if there's already notification about unread messages in this dialogue
            existing_notification = Notification.objects.filter(
                user=recipient,
                notification_type="new_message",
                related_object_id=dialogue_id,
                related_content_type="dialogue",
                is_read=False,
            ).first()

            if existing_notification:
                # Update existing notification
                existing_notification.message = _(
                    "New message from %(email)s: %(text)s%(ellipsis)s"
                ) % {
                    "email": sender.email,
                    "text": message_text[:100],
                    "ellipsis": "..." if len(message_text) > 100 else "",
                }
                existing_notification.save()
            else:
                # Create new notification
                Notification.objects.create(
                    user=recipient,
                    notification_type="new_message",
                    title=_("💬 New message"),
                    message=_("%(email)s: %(text)s%(ellipsis)s")
                    % {
                        "email": sender.email,
                        "text": message_text[:100],
                        "ellipsis": "..." if len(message_text) > 100 else "",
                    },
                    action_url=f"/chat/dialogue/{dialogue_id}/",
                    related_object_id=dialogue_id,
                    related_content_type="dialogue",
                )
            return True
        except Exception as e:
            print(f"Error creating message notification: {e}")
            return False

    @staticmethod
    def mark_dialogue_notifications_read(user, dialogue_id):
        """Mark all message notifications in dialogue as read"""
        Notification.objects.filter(
            user=user,
            notification_type="new_message",
            related_object_id=dialogue_id,
            related_content_type="dialogue",
            is_read=False,
        ).update(is_read=True)

    @staticmethod
    def delete_dialogue_notifications(user, dialogue_id):
        """Delete all message notifications in dialogue"""
        Notification.objects.filter(
            user=user,
            notification_type="new_message",
            related_object_id=dialogue_id,
            related_content_type="dialogue",
        ).delete()

    @staticmethod
    def create_cancellation_notification(order, master, customer):
        """Create order cancellation notification by buyer"""
        try:
            from orders.models import Order

            order_content_type = ContentType.objects.get_for_model(Order)

            Notification.objects.create(
                user=master,
                notification_type="order_cancelled",
                title=_("❌ Order cancelled"),
                message=_("Customer %(email)s cancelled order #%(id)s")
                % {"email": customer.email, "id": order.id},
                action_url=f"/orders/sales/",
                related_object_id=order.id,
                related_content_type=order_content_type,
            )
            return True
        except Exception as e:
            print(f"Error creating cancellation notification: {e}")
            return False

    @staticmethod
    def create_master_cancellation_notification(order, master):
        """Create order cancellation notification by master"""
        try:
            from orders.models import Order

            order_content_type = ContentType.objects.get_for_model(Order)

            Notification.objects.create(
                user=order.customer,
                notification_type="order_cancelled",
                title=_("❌ Order cancelled by master"),
                message=_("Master %(email)s cancelled your order #%(id)s")
                % {"email": master.email, "id": order.id},
                action_url=f"/orders/purchases/",
                related_object_id=order.id,
                related_content_type=order_content_type,
            )
            return True
        except Exception as e:
            print(f"Error creating master cancellation notification: {e}")
            return False

    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications"""
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read"""
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def delete_read_notifications(user):
        """Delete all read notifications"""
        deleted_count, _ = Notification.objects.filter(user=user, is_read=True).delete()
        return deleted_count

    @staticmethod
    def delete_single_notification(user, notification_id):
        """Delete single notification (read only)"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            if notification.is_read:
                notification.delete()
                return True
            return False
        except Notification.DoesNotExist:
            return False

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("api/unread-count/", views.unread_count_api, name="unread_count_api"),
    path("<int:notification_id>/mark-read/", views.mark_as_read, name="mark_as_read"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path(
        "<int:notification_id>/delete/",
        views.delete_notification,
        name="delete_notification",
    ),  # НОВЫЙ URL
    path(
        "delete-all-read/", views.delete_all_read, name="delete_all_read"
    ),  # НОВЫЙ URL
]

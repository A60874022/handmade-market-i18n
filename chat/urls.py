from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.dialogue_list, name="dialogue_list"),
    path(
        "<int:pk>/", views.dialogue_detail, name="dialogue_detail"
    ),  # было dialogue_id
    path(
        "<int:pk>/mark-read/",  # было dialogue_id
        views.mark_messages_read,
        name="mark_messages_read",
    ),
    path(
        "start/product/<int:pk>/",  #
        views.start_dialogue_from_product,
        name="start_dialogue_from_product",
    ),
    path(
        "delete/<int:pk>/", views.delete_dialogue, name="delete_dialogue"
    ),  # было dialogue_id
    path("clear-all/", views.clear_all_dialogues, name="clear_all_dialogues"),
]

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart_view"),
    path(
        "cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"
    ),  # Изменил product_id на pk
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/create-order/", views.create_order, name="create_order"),
    path("purchases/", views.purchase_orders, name="purchase_orders"),
    path("sales/", views.sale_orders, name="sale_orders"),
    path(
        "sales/delete/<int:order_id>/",
        views.delete_sale_order,
        name="delete_sale_order",
    ),
    path("purchases/<int:order_id>/delete/", views.delete_order, name="delete_order"),
]

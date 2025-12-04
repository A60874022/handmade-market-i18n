from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.ProductCatalogView.as_view(), name="catalog"),
    path("add/", views.ProductCreateView.as_view(), name="product_add"),
    path("<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path("my/", views.ProductListView.as_view(), name="my_products"),
    path(
        "<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"
    ),  # было product_id
    path("<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("autocomplete/", views.product_autocomplete, name="autocomplete"),
    path("profile/", views.profile, name="profile"),
    # Избранное
    path(
        "favorites/add/<int:pk>/", views.add_to_favorites, name="add_to_favorites"
    ),  # было product_id
    path(
        "favorites/remove/<int:pk>/",  # было favorite_id
        views.remove_from_favorites,
        name="remove_from_favorites",
    ),
    path(
        "favorites/remove_by_product/<int:pk>/",  # было product_id
        views.remove_from_favorites_by_product,
        name="remove_from_favorites_by_product",
    ),
]

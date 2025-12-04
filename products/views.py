import logging
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from orders.models import Order

from .forms import ProductForm, ProductImageFormSet
from .models import Category, Favorite, Product

logger = logging.getLogger(__name__)


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("products:my_products")

    def dispatch(self, request, *args, **kwargs):
        # ПРОВЕРКА ГОРОДА ПЕРЕД СОЗДАНИЕМ ТОВАРА
        if not hasattr(request.user, "profile") or not request.user.profile.city:
            messages.warning(
                request,
                "⚠️ Пожалуйста, укажите город в вашем профиле перед созданием товара.",
            )
            return redirect("users:edit_profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.master = self.request.user
                # Город автоматически берется из профиля через свойство city модели Product
                response = super().form_valid(form)

                formset = ProductImageFormSet(
                    self.request.POST, self.request.FILES, instance=self.object
                )
                if formset.is_valid():
                    formset.save()
                    if not self.object.images.filter(is_main=True).exists():
                        first_image = self.object.images.first()
                        if first_image:
                            first_image.is_main = True
                            first_image.save()
                else:
                    for form in formset:
                        if form.errors:
                            logger.error(
                                "Image validation errors for product %s: %s",
                                self.object.id,
                                form.errors,
                            )
                            for field, errors in form.errors.items():
                                for error in errors:
                                    messages.error(
                                        self.request, f"Ошибка в изображении: {error}"
                                    )

            messages.success(self.request, "✅ Товар успешно создан!")
            return response

        except Exception as e:
            logger.error("Product creation failed: %s", str(e), exc_info=True)
            messages.error(self.request, "Ошибка при создании товара")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = ProductImageFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            context["formset"] = ProductImageFormSet()

        # Добавляем информацию о городе в контекст
        context["user_city"] = (
            self.request.user.profile.city
            if hasattr(self.request.user, "profile")
            else None
        )
        return context


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_edit.html"
    success_url = reverse_lazy("products:my_products")

    def test_func(self):
        product = self.get_object()
        return self.request.user == product.master

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = ProductImageFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["formset"] = ProductImageFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
                formset = ProductImageFormSet(
                    self.request.POST, self.request.FILES, instance=self.object
                )

                if formset.is_valid():
                    formset.save()
                    if not self.object.images.filter(is_main=True).exists():
                        first_image = self.object.images.first()
                        if first_image:
                            first_image.is_main = True
                            first_image.save()

                else:
                    for form in formset:
                        if form.errors:
                            logger.error(
                                "Image update errors for product %s: %s",
                                self.object.id,
                                form.errors,
                            )
                            for field, errors in form.errors.items():
                                for error in errors:
                                    messages.error(
                                        self.request, f"Ошибка в изображении: {error}"
                                    )
                    return self.form_invalid(form)

            messages.success(self.request, "Товар успешно обновлен!")
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Product update failed for product %s: %s",
                self.get_object().id,
                str(e),
                exc_info=True,
            )
            messages.error(self.request, "Ошибка при обновлении товара")
            return self.form_invalid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    success_url = reverse_lazy("products:my_products")
    template_name = "products/product_confirm_delete.html"

    def get_queryset(self):
        return Product.objects.filter(master=self.request.user)

    def delete(self, request, *args, **kwargs):
        try:
            product = self.get_object()
            result = super().delete(request, *args, **kwargs)
            messages.success(request, "Товар успешно удален!")
            return result
        except Exception as e:
            logger.error(
                "Product deletion failed for product %s: %s",
                self.get_object().id,
                str(e),
                exc_info=True,
            )
            messages.error(request, "Ошибка при удалении товара")
            return redirect("products:my_products")


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "products/my_products.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.filter(master=self.request.user).order_by("-created_at")


class ProductCatalogView(ListView):
    model = Product
    template_name = "products/catalog.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        try:
            # Только активные и одобренные товары
            queryset = Product.objects.filter(
                is_active=True, is_approved=True
            ).select_related("master", "category", "master__profile__city")

            # Фильтрация по категории
            category_slug = self.request.GET.get("category")
            if category_slug:
                # НЕ используем get_object_or_404, чтобы не вызывать 404 при некорректной категории
                try:
                    category = Category.objects.get(slug=category_slug)
                    queryset = queryset.filter(category=category)
                except Category.DoesNotExist:
                    # Если категория не найдена, просто игнорируем фильтр
                    pass

            # Поиск по названию и описанию
            search_query = self.request.GET.get("q")
            if search_query:
                queryset = queryset.filter(
                    Q(title__icontains=search_query)
                    | Q(description__icontains=search_query)
                )

            # ФИЛЬТРАЦИЯ ПО ГОРОДУ
            city_query = self.request.GET.get("city")
            if city_query:
                queryset = queryset.filter(
                    Q(master__profile__city__name__icontains=city_query)
                )

            return queryset.order_by("-created_at")

        except Exception as e:
            logger.error("Error loading product catalog: %s", str(e), exc_info=True)
            return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ДОБАВЛЯЕМ КАТЕГОРИИ В КОНТЕКСТ
        context["categories"] = Category.objects.all().order_by("name")

        # Получаем список всех городов, в которых есть активные товары
        from users.models import City

        context["cities"] = (
            City.objects.filter(
                is_active=True,
                profile__user__products__is_active=True,
                profile__user__products__is_approved=True,
            )
            .distinct()
            .order_by("name")
        )

        # Добавляем информацию об избранных товарах для текущего пользователя
        if self.request.user.is_authenticated:
            context["user_favorites"] = self.request.user.favorites.values_list(
                "product_id", flat=True
            )
        else:
            context["user_favorites"] = []

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        # Владелец видит свой товар всегда, остальные - только одобренные
        if self.request.user.is_authenticated:
            return Product.objects.filter(
                Q(is_active=True, is_approved=True) | Q(master=self.request.user)
            ).select_related("master")
        else:
            return Product.objects.filter(
                is_active=True, is_approved=True
            ).select_related("master")


@login_required
def profile(request):
    """Главная страница профиля мастера с вкладками"""
    try:
        active_tab = request.GET.get("tab", "orders")

        context = {
            "active_tab": active_tab,
        }

        if active_tab == "orders":
            # Показываем заказы как покупателя
            context["orders"] = Order.objects.filter(
                customer=request.user
            ).prefetch_related("items__product")
        elif active_tab == "favorites":
            context["favorites"] = Favorite.objects.filter(
                user=request.user
            ).select_related("product")
        elif active_tab == "my_products":
            # Показываем товары мастера
            context["my_products"] = Product.objects.filter(
                master=request.user
            ).order_by("-created_at")
        elif active_tab == "master_orders":
            # Показываем заказы на товары мастера
            context["master_orders"] = Order.objects.filter(
                items__product__master=request.user
            ).distinct()

        return render(request, "users/customer_profile.html", context)

    except Exception as e:
        logger.error(
            "Error loading profile for user %s: %s",
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при загрузке профиля")
        return redirect("products:catalog")


@login_required
def add_to_favorites(request, pk):
    """Добавление товара в избранное"""
    try:
        product = get_object_or_404(Product, id=pk, is_active=True)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, product=product
        )

        if created:
            messages.success(request, f'Товар "{product.title}" добавлен в избранное')
        else:
            messages.info(request, f'Товар "{product.title}" уже в избранном')

        return redirect(request.META.get("HTTP_REFERER", "catalog"))

    except Exception as e:
        logger.error(
            "Add to favorites failed for product %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при добавлении в избранное")
        return redirect("products:catalog")


@login_required
def remove_from_favorites(request, pk):
    """Удаление товара из избранного"""
    try:
        favorite = get_object_or_404(Favorite, id=pk, user=request.user)
        product_title = favorite.product.title
        favorite.delete()

        messages.success(request, f'Товар "{product_title}" удален из избранного')
        return redirect(f"{reverse('products:profile')}?tab=favorites")

    except Exception as e:
        logger.error(
            "Remove favorite failed for favorite %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении из избранного")
        return redirect("products:profile")


@login_required
def remove_from_favorites_by_product(request, pk):
    """Удаление товара из избранного по product_id"""
    try:
        product = get_object_or_404(Product, id=pk)
        favorite = get_object_or_404(Favorite, user=request.user, product=product)
        product_title = favorite.product.title
        favorite.delete()

        messages.success(request, f'Товар "{product_title}" удален из избранного')
        return redirect(request.META.get("HTTP_REFERER", "products:catalog"))

    except Exception as e:
        logger.error(
            "Remove favorite by product failed for product %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, "Ошибка при удалении из избранного")
        return redirect(request.META.get("HTTP_REFERER", "products:catalog"))


from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def product_autocomplete(request):
    """Автодополнение для поиска товаров"""
    try:
        query = request.GET.get("q", "").strip()

        if len(query) < 2:
            return JsonResponse({"success": True, "results": []})

        # Ищем только среди одобренных товаров
        products = (
            Product.objects.filter(
                (Q(title__icontains=query) | Q(description__icontains=query)),
                is_active=True,
                is_approved=True,
            )
            .select_related("category")
            .order_by("-created_at")[:8]
        )

        results = []
        for product in products:
            main_image = product.images.filter(is_main=True).first()
            image_url = main_image.image.url if main_image else None

            category_name = (
                product.category.name if product.category else "Без категории"
            )

            results.append(
                {
                    "id": product.pk,
                    "title": product.title,
                    "category": category_name,
                    "price": str(product.price),
                    "image_url": image_url,
                    "url": reverse(
                        "products:product_detail", kwargs={"pk": product.pk}
                    ),
                }
            )

        return JsonResponse({"success": True, "results": results})

    except Exception as e:
        logger.error("Autocomplete error for query '%s': %s", query, str(e))
        return JsonResponse({"success": False, "results": []})

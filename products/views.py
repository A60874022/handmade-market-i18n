#
import uuid 
import logging
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _
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
        # CHECK CITY BEFORE CREATING PRODUCT
        if not hasattr(request.user, "profile") or not request.user.profile.city:
            messages.warning(
                request,
                _(
                    "⚠️ Please specify your city in your profile before creating a product."
                ),
            )
            return redirect("users:edit_profile")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Передаем request в форму для фильтрации категорий"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.master = self.request.user
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
                                        self.request,
                                        _("Error in image: %(error)s")
                                        % {"error": error},
                                    )

            messages.success(self.request, _("✅ Product successfully created!"))
            return response

        except Exception as e:
            logger.error("Product creation failed: %s", str(e), exc_info=True)
            messages.error(self.request, _("Error creating product"))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = ProductImageFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            context["formset"] = ProductImageFormSet()

        # Add city information to context
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

    def get_form_kwargs(self):
        """Передаем request в форму для фильтрации категорий"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

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
                                        self.request,
                                        _("Error in image: %(error)s")
                                        % {"error": error},
                                    )
                    return self.form_invalid(form)

            messages.success(self.request, _("Product successfully updated!"))
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Product update failed for product %s: %s",
                self.get_object().id,
                str(e),
                exc_info=True,
            )
            messages.error(self.request, _("Error updating product"))
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
            messages.success(request, _("Product successfully deleted!"))
            return result
        except Exception as e:
            logger.error(
                "Product deletion failed for product %s: %s",
                self.get_object().id,
                str(e),
                exc_info=True,
            )
            messages.error(request, _("Error deleting product"))
            return redirect("products:my_products")


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "products/my_products.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.filter(master=self.request.user).order_by("-created_at")


import logging

from django.db.models import Q
from django.views.generic import ListView

logger = logging.getLogger(__name__)

from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class ProductCatalogView(ListView):
    model = Product
    template_name = "products/catalog.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        try:
            qs = Product.objects.filter(
                is_active=True, is_approved=True
            ).select_related("master", "category", "master__profile__city")

            # ФИЛЬТРАЦИЯ ПО ГРУППЕ ПЕРЕВОДОВ КАТЕГОРИЙ
            translation_group_param = self.request.GET.get("category")
            if translation_group_param:
                try:
                    # Пытаемся получить translation_group из параметра
                    translation_group = uuid.UUID(translation_group_param)
                    # Находим все категории в этой группе переводов
                    categories_in_group = Category.objects.filter(
                        translation_group=translation_group,
                        is_active=True
                    )
                    # Фильтруем продукты по всем категориям в группе
                    qs = qs.filter(category__in=categories_in_group)
                except (ValueError, TypeError):
                    # Если параметр не UUID, пробуем найти по slug (для обратной совместимости)
                    try:
                        category = Category.objects.get(
                            slug=translation_group_param,
                            is_active=True
                        )
                        qs = qs.filter(category__in=category.get_translations())
                    except Category.DoesNotExist:
                        logger.warning(f"Category not found: {translation_group_param}")

            # Поиск по названию и описанию
            search_query = self.request.GET.get("q")
            if search_query:
                qs = qs.filter(
                    Q(title__icontains=search_query) | 
                    Q(description__icontains=search_query)
                )

            # Фильтр по городу
            city_param = self.request.GET.get("city")
            if city_param:
                try:
                    city_id = int(city_param)
                    qs = qs.filter(master__profile__city_id=city_id)
                except (ValueError, TypeError):
                    logger.debug(f"Invalid city id: {city_param}")

            return qs.order_by("-created_at")

        except Exception as e:
            logger.error(f"Error loading product catalog: {e}", exc_info=True)
            return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем текущий язык пользователя
        current_language = self.request.LANGUAGE_CODE if hasattr(self.request, 'LANGUAGE_CODE') else 'en'
        
        # Показываем только категории на текущем языке пользователя
        context["categories"] = Category.objects.filter(
            language_code=current_language,
            is_active=True
        ).order_by("name")
        
        # Также передаем выбранную категорию для отображения в активных фильтрах
        selected_translation_group = self.request.GET.get("category")
        if selected_translation_group:
            try:
                translation_group = uuid.UUID(selected_translation_group)
                # Находим категорию на текущем языке в этой группе
                selected_category = Category.objects.filter(
                    translation_group=translation_group,
                    language_code=current_language,
                    is_active=True
                ).first()
                if selected_category:
                    context["selected_category"] = selected_category
            except (ValueError, TypeError):
                # Для обратной совместимости
                selected_category = Category.objects.filter(
                    slug=selected_translation_group,
                    is_active=True
                ).first()
                if selected_category:
                    context["selected_category"] = selected_category

        # Города
        try:
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
        except Exception as e:
            logger.error(f"Error loading cities: {e}")
            context["cities"] = []

        # Избранное
        if self.request.user.is_authenticated:
            context["user_favorites"] = list(
                self.request.user.favorites.values_list("product_id", flat=True)
            )
        else:
            context["user_favorites"] = []

        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        # Owner always sees their product, others - only approved ones
        if self.request.user.is_authenticated:
            return Product.objects.filter(
                Q(is_active=True, is_approved=True) | Q(master=self.request.user)
            ).select_related("master", "master__profile")
        else:
            return Product.objects.filter(
                is_active=True, is_approved=True
            ).select_related("master", "master__profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = context['product']
        
        # Проверяем, является ли текущий пользователь владельцем товара
        context['is_own_product'] = self.request.user == product.master
            
        return context


@login_required
def profile(request):
    """Master profile main page with tabs"""
    try:
        active_tab = request.GET.get("tab", "orders")

        context = {
            "active_tab": active_tab,
        }

        if active_tab == "orders":
            # Show orders as buyer
            context["orders"] = Order.objects.filter(
                customer=request.user
            ).prefetch_related("items__product")
        elif active_tab == "favorites":
            context["favorites"] = Favorite.objects.filter(
                user=request.user
            ).select_related("product")
        elif active_tab == "my_products":
            # Show master products
            context["my_products"] = Product.objects.filter(
                master=request.user
            ).order_by("-created_at")
        elif active_tab == "master_orders":
            # Show orders for master products
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
        messages.error(request, _("Error loading profile"))
        return redirect("products:catalog")


@login_required
def add_to_favorites(request, pk):
    """Add product to favorites"""
    try:
        product = get_object_or_404(Product, id=pk, is_active=True)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, product=product
        )

        if created:
            messages.success(
                request,
                _('Product "%(title)s" added to favorites') % {"title": product.title},
            )
        else:
            messages.info(
                request,
                _('Product "%(title)s" is already in favorites')
                % {"title": product.title},
            )

        return redirect(request.META.get("HTTP_REFERER", "catalog"))

    except Exception as e:
        logger.error(
            "Add to favorites failed for product %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error adding to favorites"))
        return redirect("products:catalog")


@login_required
def remove_from_favorites(request, pk):
    """Remove product from favorites"""
    try:
        favorite = get_object_or_404(Favorite, id=pk, user=request.user)
        product_title = favorite.product.title
        favorite.delete()

        messages.success(
            request,
            _('Product "%(title)s" removed from favorites') % {"title": product_title},
        )
        return redirect(f"{reverse('products:profile')}?tab=favorites")

    except Exception as e:
        logger.error(
            "Remove favorite failed for favorite %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error removing from favorites"))
        return redirect("products:profile")


@login_required
def remove_from_favorites_by_product(request, pk):
    """Remove product from favorites by product_id"""
    try:
        product = get_object_or_404(Product, id=pk)
        favorite = get_object_or_404(Favorite, user=request.user, product=product)
        product_title = favorite.product.title
        favorite.delete()

        messages.success(
            request,
            _('Product "%(title)s" removed from favorites') % {"title": product_title},
        )
        return redirect(request.META.get("HTTP_REFERER", "products:catalog"))

    except Exception as e:
        logger.error(
            "Remove favorite by product failed for product %s by user %s: %s",
            pk,
            request.user.id,
            str(e),
            exc_info=True,
        )
        messages.error(request, _("Error removing from favorites"))
        return redirect(request.META.get("HTTP_REFERER", "products:catalog"))


from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def product_autocomplete(request):
    """Autocomplete for product search"""
    try:
        query = request.GET.get("q", "").strip()

        if len(query) < 2:
            return JsonResponse({"success": True, "results": []})

        # Search only among approved products
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
                product.category.name if product.category else _("No category")
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

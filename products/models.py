from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Замечание 17: Сохраняем название с заглавной буквы
        if self.name:
            self.name = self.name.capitalize()
        super().save(*args, **kwargs)


from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse  # Добавьте этот импорт


class Product(models.Model):
    MAX_PRICE = 5000000

    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Мастер",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория",
    )
    title = models.CharField(
        max_length=60,
        verbose_name="Название",
        validators=[
            RegexValidator(
                regex="^[а-яА-ЯёЁ0-9\s\-\!\.\(\)]+$",
                message="Название должно содержать только кириллические символы, цифры и пробелы",
            )
        ],
    )
    description = models.TextField(
        max_length=300,
        verbose_name="Описание",
        validators=[
            RegexValidator(
                regex="^[а-яА-ЯёЁ0-9\s\-\!\.\(\)\,\:\;]+$",
                message="Описание должно содержать только кириллические символы, цифры и знаки препинания",
            )
        ],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена",
        validators=[
            MinValueValidator(1, message="Цена должна быть не менее 1 рубля"),
            MaxValueValidator(
                MAX_PRICE, message=f"Цена не может превышать {MAX_PRICE:,} рублей"
            ),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    is_approved = models.BooleanField(
        default=False, verbose_name="Одобрено модератором"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Возвращает абсолютный URL для товара"""
        return reverse("products:product_detail", kwargs={"pk": self.pk})

    @property
    def city(self):
        """Автоматически получаем город из профиля мастера"""
        if hasattr(self.master, "profile") and self.master.profile.city:
            return self.master.profile.city
        return None

    def get_city_display(self):
        """Возвращает отображаемое название города"""
        city = self.city
        if city:
            return city.name
        return "Город не указан"

    def get_main_image(self):
        """Возвращает главное изображение товара"""
        try:
            main_image = self.images.filter(is_main=True).first()
            if main_image:
                return main_image
            return self.images.first()
        except:
            return None

    def has_images(self):
        """Проверяет, есть ли у товара изображения"""
        return self.images.exists()

    def is_visible(self):
        """Товар виден, если активен и одобрен"""
        return self.is_active and self.is_approved


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="product_images/", verbose_name="Изображение")
    is_main = models.BooleanField(default=False, verbose_name="Основное изображение")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

    def __str__(self):
        return f"Изображение {self.product.title}"

    def save(self, *args, **kwargs):
        # Замечание 21: Ограничиваем одну основную фотографию
        if self.is_main:
            # Снимаем флаг is_main у всех других изображений этого товара
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(
                pk=self.pk
            ).update(is_main=False)
        super().save(*args, **kwargs)


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные товары"
        unique_together = ["user", "product"]

    def __str__(self):
        return f"{self.user.email} - {self.product.title}"

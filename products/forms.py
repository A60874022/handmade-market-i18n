from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "title", "description", "price"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: Вязаная шерстяная шапка",
                    "maxlength": "60",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Опишите ваш товар, материалы, размеры...",
                    "maxlength": "300",
                }
            ),
            # ИЗМЕНЕНО: NumberInput на TextInput для снятия ограничений браузера
            "price": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "inputmode": "numeric",  # Показывает цифровую клавиатуру на мобильных
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Замечание 18: Добавляем валидаторы для кириллицы
        self.fields["title"].validators.append(
            RegexValidator(
                regex="^[а-яА-ЯёЁ0-9\s\-\!\.\(\)]+$",
                message="Название должно содержать только кириллические символы, цифры и пробелы",
            )
        )
        self.fields["description"].validators.append(
            RegexValidator(
                regex="^[а-яА-ЯёЁ0-9\s\-\!\.\(\)\,\:\;]+$",
                message="Описание должно содержать только кириллические символы, цифры и знаки препинания",
            )
        )

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is None or price == "":
            raise forms.ValidationError("Введите цену товара")

        try:
            # Преобразуем строку в число
            price_int = int(price)
        except (ValueError, TypeError):
            raise forms.ValidationError("Введите корректную цену (только цифры)")

        # Проверяем границы цены
        if price_int < 1:
            raise forms.ValidationError("Цена должна быть не менее 1 рубля")

        if price_int > 5000000:
            raise forms.ValidationError("Цена не может превышать 5 000 000 рублей")

        return price_int

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title:
            if len(title) > 60:
                raise forms.ValidationError("Название не может превышать 60 символов")
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            if len(description) > 300:
                raise forms.ValidationError("Описание не может превышать 300 символов")
        return description


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main"]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "is_main": forms.CheckboxInput(
                attrs={"class": "form-check-input main-image-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле image необязательным для существующих записей
        if self.instance and self.instance.pk:
            self.fields["image"].required = False


# Замечание 20: Уточняем количество фото (включительно до 4)
ProductImageFormSet = forms.inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=4,  # Можно загрузить до 4 фото включительно
    can_delete=True,
    max_num=4,  # Максимум 4 фото
)

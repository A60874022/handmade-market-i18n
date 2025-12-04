# users/management/commands/load_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category


class Command(BaseCommand):
    help = "Загрузка категорий для handmade-товаров"

    def handle(self, *args, **options):
        categories = [
            # Основные категории рукоделия
            "Ювелирные изделия",
            "Бижутерия",
            "Вязаные изделия",
            "Вышивка",
            "Шитьё",
            "Керамика",
            "Стекло",
            "Деревянные изделия",
            "Кожаные изделия",
            "Мыло ручной работы",
            "Свечи",
            "Косметика ручной работы",
            # Художественные категории
            "Живопись",
            "Графика",
            "Фотография",
            "Скульптура",
            "Каллиграфия",
            # Праздничные и тематические
            "Подарки",
            "Новогодние украшения",
            "Свадебные аксессуары",
            "Детские товары",
            # Для дома и интерьера
            "Декор для дома",
            "Текстиль для дома",
            "Кухонные принадлежности",
            "Садовый декор",
            # Модные аксессуары
            "Сумки",
            "Головные уборы",
            "Шарфы и платки",
            "Перчатки и варежки",
            # Техники и материалы
            "Валяние",
            "Бисероплетение",
            "Макраме",
            "Пэчворк",
            "Скрапбукинг",
            "Декупаж",
            # Куклы и игрушки
            "Авторские куклы",
            "Тедди-мишки",
            "Развивающие игрушки",
            # Канцелярия и бумага
            "Блокноты и тетради",
            "Открытки",
            "Упаковка",
            # Мужские товары
            "Аксессуары для мужчин",
            # Эко-товары
            "Эко-товары",
        ]

        categories_created = 0
        categories_updated = 0

        for name in categories:
            slug = slugify(name, allow_unicode=True)

            category, created = Category.objects.update_or_create(
                name=name, defaults={"slug": slug}
            )

            if created:
                categories_created += 1
                self.stdout.write(f"Создана категория: {name}")
            else:
                categories_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно загружено категорий: создано {categories_created}, обновлено {categories_updated}"
            )
        )

# users/management/commands/load_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category


class Command(BaseCommand):
    help = "Загрузка категорий для handmade-товаров на английском, немецком и французском языках"

    def handle(self, *args, **options):
        categories = [
            # English categories
            "Jewelry",
            "Knitted items",
            "Ceramics",
            "Home decor",
            "Leather goods",
            "Handmade cosmetics",
            
            # German categories
            "Schmuck",
            "Strickwaren",
            "Keramik",
            "Wohndeko",
            "Lederwaren",
            "Handgemachte Kosmetik",
            
            # French categories
            "Bijoux",
            "Articles tricotés",
            "Céramique",
            "Décoration intérieure",
            "Articles en cuir",
            "Cosmétiques artisanaux",
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
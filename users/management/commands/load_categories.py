# users/management/commands/load_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
import uuid

from products.models import Category


class Command(BaseCommand):
    help = "Загрузка категорий для handmade-товаров на английском, немецком и французском языках"

    def handle(self, *args, **options):
        # Определяем группы переводов для каждой категории
        # Каждая группа содержит переводы на разных языках
        category_groups = [
            {
                'en': 'Jewelry',
                'de': 'Schmuck',
                'fr': 'Bijoux'
            },
            {
                'en': 'Knitted items',
                'de': 'Strickwaren',
                'fr': 'Articles tricotés'
            },
            {
                'en': 'Ceramics',
                'de': 'Keramik',
                'fr': 'Céramique'
            },
            {
                'en': 'Home decor',
                'de': 'Wohndeko',
                'fr': 'Décoration intérieure'
            },
            {
                'en': 'Leather goods',
                'de': 'Lederwaren',
                'fr': 'Articles en cuir'
            },
            {
                'en': 'Handmade cosmetics',
                'de': 'Handgemachte Kosmetik',
                'fr': 'Cosmétiques artisanaux'
            },
        ]

        categories_created = 0
        categories_updated = 0
        groups_processed = 0

        for group in category_groups:
            # Создаем уникальную группу переводов для этой категории
            translation_group = uuid.uuid4()
            
            for lang_code, name in group.items():
                # Генерируем slug с языковым суффиксом
                base_slug = slugify(name, allow_unicode=True)
                slug = f"{base_slug}-{lang_code}"
                
                try:
                    # Пытаемся найти существующую категорию с таким именем и языком
                    category = Category.objects.filter(
                        name=name,
                        language_code=lang_code
                    ).first()
                    
                    if category:
                        # Обновляем существующую категорию
                        category.translation_group = translation_group
                        category.slug = slug
                        category.is_active = True
                        category.save()
                        categories_updated += 1
                        self.stdout.write(f"Обновлена категория: {name} ({lang_code})")
                    else:
                        # Создаем новую категорию
                        Category.objects.create(
                            name=name,
                            slug=slug,
                            language_code=lang_code,
                            translation_group=translation_group,
                            is_active=True
                        )
                        categories_created += 1
                        self.stdout.write(f"Создана категория: {name} ({lang_code})")
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Ошибка при обработке категории {name} ({lang_code}): {e}")
                    )
            
            groups_processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно загружено категорий: создано {categories_created}, обновлено {categories_updated}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Обработано групп переводов: {groups_processed}"
            )
        )
        
        # Проверяем целостность данных
        self.stdout.write("\n" + "="*50)
        self.stdout.write("Проверка целостности данных:")
        
        # Показываем статистику по языкам
        for lang_code in ['en', 'de', 'fr']:
            count = Category.objects.filter(language_code=lang_code, is_active=True).count()
            self.stdout.write(f"  {lang_code.upper()}: {count} категорий")
        
        # Показываем примеры групп переводов
        self.stdout.write("\nПримеры групп переводов:")
        for i, group in enumerate(category_groups[:3], 1):  # Показываем первые 3 группы
            en_name = group['en']
            # Находим категорию на английском
            en_category = Category.objects.filter(
                name=en_name,
                language_code='en'
            ).first()
            
            if en_category:
                translations = Category.objects.filter(
                    translation_group=en_category.translation_group,
                    is_active=True
                )
                lang_names = [f"{cat.name} ({cat.language_code})" for cat in translations]
                self.stdout.write(f"  Группа {i}: {', '.join(lang_names)}")
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from menu.models import Category, MenuItem
from service.models import DiningTable


class Command(BaseCommand):
    help = "Создаёт начальное меню, столы и учётные записи персонала"

    def handle(self, *args, **options):
        self._seed_users()
        self._seed_tables()
        self._seed_menu()
        self.stdout.write(self.style.SUCCESS("Начальные данные готовы."))

    def _seed_users(self):
        users = [
            ("admin", User.Role.ADMIN, settings.SEED_ADMIN_PASSWORD, "Админ", True),
            ("waiter", User.Role.WAITER, settings.SEED_WAITER_PASSWORD, "Официант", False),
            ("cook", User.Role.COOK, settings.SEED_COOK_PASSWORD, "Повар", False),
        ]
        for username, role, password, first_name, is_superuser in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "first_name": first_name,
                    "is_staff": is_superuser or role == User.Role.ADMIN,
                    "is_superuser": is_superuser,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"Создан пользователь {username}")
            else:
                # Keep existing password; refresh role/flags if needed.
                changed = False
                if user.role != role:
                    user.role = role
                    changed = True
                if is_superuser and not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                    changed = True
                if changed:
                    user.save()

    def _seed_tables(self):
        for number in range(1, 11):
            DiningTable.objects.get_or_create(
                number=number,
                defaults={"seats": 4 if number < 9 else 6, "is_active": True},
            )

    def _seed_menu(self):
        if MenuItem.objects.exists():
            return

        drinks, _ = Category.objects.get_or_create(
            name="Напитки",
            defaults={"sort_order": 1, "is_active": True},
        )
        desserts, _ = Category.objects.get_or_create(
            name="Десерты",
            defaults={"sort_order": 2, "is_active": True},
        )
        mains, _ = Category.objects.get_or_create(
            name="Основные блюда",
            defaults={"sort_order": 3, "is_active": True},
        )

        items = [
            (drinks, "Эспрессо", "Классический крепкий кофе", "150.00", 1),
            (drinks, "Капучино", "С молочной пенкой", "220.00", 2),
            (drinks, "Чай чёрный", "Листовой чай", "180.00", 3),
            (desserts, "Чизкейк", "Классический нью-йорк", "320.00", 1),
            (desserts, "Брауни", "С орехами", "280.00", 2),
            (mains, "Круассан с сыром", "Тёплый круассан", "250.00", 1),
            (mains, "Омлет", "С томатами и зеленью", "290.00", 2),
            (mains, "Салат Цезарь", "С курицей", "390.00", 3),
        ]
        for category, name, description, price, sort_order in items:
            MenuItem.objects.create(
                category=category,
                name=name,
                description=description,
                price=Decimal(price),
                sort_order=sort_order,
                is_available=True,
            )

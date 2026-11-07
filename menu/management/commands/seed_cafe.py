from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import User
from menu.models import Category, MenuItem, invalidate_menu_cache
from service.models import DiningTable

SEED_PHOTOS = Path(settings.MEDIA_ROOT) / "seed_photos"

CATEGORIES = [
    {
        "name": "Холодные закуски и салаты",
        "subtitle": "Свежие салаты, сыры и закуски",
        "icon": "🥗",
        "sort_order": 1,
    },
    {
        "name": "Первые блюда",
        "subtitle": "Супы домашние и сезонные",
        "icon": "🍲",
        "sort_order": 2,
    },
    {
        "name": "Горячие блюда и гриль",
        "subtitle": "Мангал, паста и горячие хиты",
        "icon": "🥩",
        "sort_order": 3,
    },
    {
        "name": "Детское меню",
        "subtitle": "Блюда для маленьких гостей",
        "icon": "🧒",
        "sort_order": 4,
    },
    {
        "name": "Десерты",
        "subtitle": "Сладкое завершение обеда",
        "icon": "🍰",
        "sort_order": 5,
    },
    {
        "name": "Напитки",
        "subtitle": "Лимонады, коктейли и кофе",
        "icon": "🥤",
        "sort_order": 6,
    },
]

# Цены в BYN. Пересчёт с прежних RUB по курсу НБРБ: 100 RUB = 3,6535 BYN (07.11.2026).
# name, category, portion, description, price, sort_order, photo_file
MENU_SEED = [
    # Салаты и закуски
    ("Салат «Греческий»", "Холодные закуски и салаты", "250 г",
     "Классика из сочных томатов, хрустящих огурцов, сладкого перца, красного лука, оливок и нежного сыра Фета, заправленная оливковым маслом с орегано.",
     "15.34", 1, "greek-salad.jpg"),
    ("Салат «Цезарь» с курицей", "Холодные закуски и салаты", "220 г",
     "Хрустящий романо, обжаренное куриное филе, хрустящие сухарики, пармезан и фирменный соус Цезарь.",
     "17.90", 2, "caesar-salad.jpg"),
    ("Салат «Мангал»", "Холодные закуски и салаты", "200 г",
     "Мясное ассорти (говядина и курица) на подушке из свежих овощей и зелени с пикантной заправкой.",
     "20.46", 3, "mangal-salad.jpg"),
    ("Сырная тарелка", "Холодные закуски и салаты", "250 г",
     "Ассорти из европейских и кавказских сыров с медом, орехами и виноградом.",
     "25.21", 4, "cheese-plate.jpg"),
    ("Рулетики из баклажанов", "Холодные закуски и салаты", "150 г",
     "Обжаренные баклажаны с нежной начинкой из грецких орехов, чеснока и зелени.",
     "13.88", 5, "eggplant-rolls.jpg"),
    # Супы
    ("Борщ с говядиной", "Первые блюда", "300 г",
     "Наваристый, томленый по домашнему рецепту, с ложкой сметаны и ароматной пампушкой с чесноком.",
     "14.25", 1, "borsch.jpg"),
    ("Куриный суп-лапша", "Первые блюда", "250 г",
     "Легкий и прозрачный бульон с домашней лапшой, кусочками куриного филе и свежей зеленью.",
     "11.69", 2, "chicken-noodle.jpg"),
    ("Солянка мясная", "Первые блюда", "280/20 г",
     "Сытный суп с копченостями, колбасными изделиями, оливками, лимоном и сметаной.",
     "16.44", 3, "solyanka.jpg"),
    ("Харчо с говядиной", "Первые блюда", "350 г",
     "Пряный, острый грузинский суп с рисом, говядиной и большим количеством зелени.",
     "15.71", 4, "kharcho.jpg"),
    ("Суп с фрикадельками", "Первые блюда", "250 г",
     "Домашний суп на курином бульоне с нежными мясными фрикадельками и овощами.",
     "12.42", 5, "meatball-soup.jpg"),
    ("Окрошка на квасе", "Первые блюда", "300 г",
     "Летний холодный суп с ветчиной, свежими овощами, яйцом и сметаной.",
     "13.15", 6, "okroshka.jpg"),
    # Горячее и гриль
    ("Шашлык из свиной шейки", "Горячие блюда и гриль", "100/50 г",
     "Сочный, маринованный по секретному рецепту, обжаренный на углях, подается с луком и зеленью.",
     "19.00", 1, "shashlik.jpg"),
    ("Люля-кебаб из баранины", "Горячие блюда и гриль", "170 г",
     "Рубленое мясо молодого барашка с луком и специями, приготовленное на мангале.",
     "21.56", 2, "lyulya.jpg"),
    ("Овощи на мангале", "Горячие блюда и гриль", "150 г",
     "Шампиньоны, томаты, болгарский перец и баклажаны, обжаренные на углях с оливковым маслом.",
     "13.88", 3, "grilled-veg.jpg"),
    ("Куриное филе в сливочном соусе", "Горячие блюда и гриль", "100/150 г",
     "Нежное филе курицы, томленое в сливках с шампиньонами, подается с картофельным пюре.",
     "20.46", 4, "chicken-cream.jpg"),
    ("Спагетти Болоньезе", "Горячие блюда и гриль", "250 г",
     "Паста аль денте с насыщенным мясным соусом болоньезе, томатами и пармезаном.",
     "17.90", 5, "bolognese.jpg"),
    ("Фахитос с курицей", "Горячие блюда и гриль", "350 г",
     "Обжаренные полоски куриного филе с овощами и специями, подаются на горячей сковороде.",
     "22.65", 6, "fajitas.jpg"),
    ("Голубцы", "Горячие блюда и гриль", "250/50 г",
     "Классические голубцы из капусты с мясным фаршем и рисом, томленые в томатно-сметанном соусе.",
     "17.54", 7, "golubtsy.jpg"),
    ("Бефстроганов", "Горячие блюда и гриль", "150/150 г",
     "Нежные кусочки говядины в сливочно-грибном соусе, подаются с картофельным пюре.",
     "23.75", 8, "beefstroganoff.jpg"),
    # Детское
    ("Сырники со сметаной", "Детское меню", "100/50 г",
     "Нежные, творожные, слегка сладкие, с румяной корочкой. Подаются со сметаной.",
     "10.23", 1, "syrniki.jpg"),
    ("Блинчики от Фунтика", "Детское меню", "140/30 г",
     "Тонкие блинчики с начинками: творог, сгущенка или домашнее варенье.",
     "9.50", 2, "blini.jpg"),
    ("Куриные наггетсы", "Детское меню", "120/30 г",
     "Хрустящее куриное филе в панировке с картофелем фри и соусом.",
     "12.42", 3, "nuggets.jpg"),
    ("Гречка с молоком", "Детское меню", "230 г",
     "Рассыпчатая гречневая каша с теплым молоком.",
     "6.94", 4, "buckwheat.jpg"),
    ("Омлет с сыром", "Детское меню", "120 г",
     "Пышный омлет из отборных яиц с добавлением сыра.",
     "8.04", 5, "kids-omelette.jpg"),
    # Десерты
    ("Чизкейк классический", "Десерты", "130 г",
     "Нежный сливочный сыр на песочной основе с ягодным топпингом.",
     "11.69", 1, "cheesecake.jpg"),
    ("Тирамису", "Десерты", "130 г",
     "Итальянский десерт с маскарпоне, кофе и какао.",
     "12.42", 2, "tiramisu.jpg"),
    ("Мороженое", "Десерты", "60 г",
     "Шарики пломбира с фруктовым или шоколадным соусом.",
     "6.58", 3, "icecream.jpg"),
    # Напитки
    ("Молочный коктейль", "Напитки", "0,35 л",
     "Взбитое молоко с мороженым: ваниль, шоколад или клубника.",
     "10.23", 1, "milkshake.jpg"),
    ("Домашний лимонад", "Напитки", "0,5 л",
     "Домашний лимонад на основе свежих цитрусов и мяты.",
     "9.50", 2, "lemonade.jpg"),
    ("Капучино", "Напитки", "0,25 л",
     "Классический капучино с плотной молочной пенкой.",
     "8.04", 3, "cappuccino.jpg"),
]


class Command(BaseCommand):
    help = "Создаёт начальное меню, столы и учётные записи персонала"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-menu",
            action="store_true",
            help="Обновить категории и блюда по актуальному ТЗ (старые позиции деактивируются)",
        )
        parser.add_argument(
            "--force-photos",
            action="store_true",
            help="Перезаписать фото блюд из media/seed_photos",
        )

    def handle(self, *args, **options):
        self._seed_users()
        self._seed_tables()
        self._seed_menu(refresh=options["refresh_menu"])
        self._attach_photos(force=options["force_photos"])
        invalidate_menu_cache()
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

    def _seed_menu(self, refresh: bool = False):
        categories = {}
        keep_category_names = {c["name"] for c in CATEGORIES}
        keep_item_names = {row[0] for row in MENU_SEED}

        for data in CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=data["name"],
                defaults={
                    "subtitle": data["subtitle"],
                    "icon": data["icon"],
                    "sort_order": data["sort_order"],
                    "is_active": True,
                },
            )
            if not created and refresh:
                category.subtitle = data["subtitle"]
                category.icon = data["icon"]
                category.sort_order = data["sort_order"]
                category.is_active = True
                category.save()
            categories[data["name"]] = category

        if refresh:
            Category.objects.exclude(name__in=keep_category_names).update(is_active=False)

        create_all = not MenuItem.objects.exists()
        if not create_all and not refresh:
            return

        for name, category_name, portion, description, price, sort_order, _photo in MENU_SEED:
            category = categories[category_name]
            item, created = MenuItem.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "portion": portion,
                    "description": description,
                    "price": Decimal(price),
                    "sort_order": sort_order,
                    "is_available": True,
                },
            )
            if not created and refresh:
                item.category = category
                item.portion = portion
                item.description = description
                item.price = Decimal(price)
                item.sort_order = sort_order
                item.is_available = True
                item.save()

        if refresh:
            MenuItem.objects.exclude(name__in=keep_item_names).update(is_available=False)

    def _attach_photos(self, force: bool = False):
        if not SEED_PHOTOS.exists():
            self.stdout.write(self.style.WARNING(f"Нет папки с фото: {SEED_PHOTOS}"))
            return

        attached = 0
        for name, _category, _portion, _description, _price, _sort, photo_name in MENU_SEED:
            item = MenuItem.objects.filter(name=name).first()
            if not item:
                continue
            photo_path = SEED_PHOTOS / photo_name
            if not photo_path.exists():
                continue
            if item.photo and not force:
                continue
            with photo_path.open("rb") as handle:
                item.photo.save(photo_name, File(handle), save=True)
            attached += 1
            self.stdout.write(f"Фото: {name} ← {photo_name}")

        if attached:
            self.stdout.write(self.style.SUCCESS(f"Привязано фото: {attached}"))

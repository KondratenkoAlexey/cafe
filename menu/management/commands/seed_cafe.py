from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from menu.models import Category, MenuItem, invalidate_menu_cache
from menu.seed_details import DISH_DETAILS
from service.models import DiningTable

# Единственная папка с фото блюд (и для seed, и для ImageField upload_to="menu/").
MENU_PHOTOS = Path(settings.MEDIA_ROOT) / "menu"

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
        "name": "Суши и роллы",
        "subtitle": "Классика и фирменные роллы",
        "icon": "🍣",
        "sort_order": 4,
    },
    {
        "name": "Пицца",
        "subtitle": "На тонком тесте из печи",
        "icon": "🍕",
        "sort_order": 5,
    },
    {
        "name": "Детское меню",
        "subtitle": "Блюда для маленьких гостей",
        "icon": "🧒",
        "sort_order": 6,
    },
    {
        "name": "Десерты",
        "subtitle": "Сладкое завершение обеда",
        "icon": "🍰",
        "sort_order": 7,
    },
    {
        "name": "Напитки",
        "subtitle": "Лимонады, коктейли и кофе",
        "icon": "🥤",
        "sort_order": 8,
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
    # Суши и роллы
    ("Ролл «Филадельфия»", "Суши и роллы", "8 шт / 240 г",
     "Нежный лосось, сливочный сыр и огурец в рисе на нори — мягкий сливочный вкус и свежая рыба.",
     "24.90", 1, "sushi-philadelphia.jpg"),
    ("Ролл «Калифорния»", "Суши и роллы", "8 шт / 220 г",
     "Снежный краб, авокадо и огурец в икре тобико — хруст снаружи и сочная начинка внутри.",
     "22.50", 2, "sushi-california.jpg"),
    ("Ролл «Дракон»", "Суши и роллы", "8 шт / 260 г",
     "Угорь унаги, авокадо и огурец под соусом унаги и кунжутом — сладковато-копчёный акцент.",
     "27.80", 3, "sushi-dragon.jpg"),
    ("Ролл «Спайси лосось»", "Суши и роллы", "8 шт / 230 г",
     "Лосось, огурец и спайси-соус на майонезе с чили — лёгкая острота и яркий рыбный вкус.",
     "23.90", 4, "sushi-spicy-salmon.jpg"),
    ("Ролл «Унаги»", "Суши и роллы", "8 шт / 250 г",
     "Копчёный угорь, сливочный сыр и огурец с соусом унаги — сытный и ароматный ролл.",
     "26.40", 5, "sushi-unagi.jpg"),
    ("Ролл «Темпура»", "Суши и роллы", "8 шт / 280 г",
     "Креветка в хрустящем кляре, авокадо и сыр, обжаренные до золотистой корочки.",
     "25.60", 6, "sushi-tempura.jpg"),
    ("Маки с лососем", "Суши и роллы", "6 шт / 120 г",
     "Классические тонкие маки: рис, нори и свежий лосось без лишних добавок.",
     "14.90", 7, "sushi-sake-maki.jpg"),
    ("Ролл с авокадо", "Суши и роллы", "8 шт / 200 г",
     "Вегетарианский ролл с спелым авокадо, огурцом и кунжутом — мягкий и свежий.",
     "16.80", 8, "sushi-avocado.jpg"),
    ("Нигири с тунцом", "Суши и роллы", "2 шт / 80 г",
     "Плотный рис под ломтиком свежего тунца — чистый вкус рыбы и лёгкая текстура.",
     "12.50", 9, "sushi-tuna-nigiri.jpg"),
    ("Гунканы с тобико", "Суши и роллы", "4 шт / 100 г",
     "Рис в полоске нори с икрой летучей рыбы — солоноватый хруст и яркий цвет.",
     "15.20", 10, "sushi-tobiko.jpg"),
    ("Сет «Сакура»", "Суши и роллы", "24 шт / 650 г",
     "Ассорти из «Филадельфии», «Калифорнии» и маки с лососем — удобно делить на компанию.",
     "49.90", 11, "sushi-sakura-set.jpg"),
    ("Ролл с креветкой", "Суши и роллы", "8 шт / 230 г",
     "Тигровая креветка, огурец и сливочный сыр в рисе — нежный морской вкус.",
     "24.20", 12, "sushi-shrimp.jpg"),
    # Пицца
    ("Пицца «Маргарита»", "Пицца", "30 см",
     "Томатный соус, моцарелла и свежий базилик на тонком тесте — классика Неаполя.",
     "21.90", 1, "pizza-margherita.jpg"),
    ("Пицца «Пепперони»", "Пицца", "30 см",
     "Острая колбаса пепперони, моцарелла и томатный соус — пикантная и сытная.",
     "25.40", 2, "pizza-pepperoni.jpg"),
    ("Пицца «Четыре сыра»", "Пицца", "30 см",
     "Моцарелла, горгонзола, пармезан и чеддер на сливочной основе — насыщенный сырный вкус.",
     "27.20", 3, "pizza-quatro-formaggi.jpg"),
    ("Пицца «Гавайская»", "Пицца", "30 см",
     "Ветчина, ананас и моцарелла — сладко-солёное сочетание на тонком тесте.",
     "24.60", 4, "pizza-hawaiian.jpg"),
    ("Пицца «Диабло»", "Пицца", "30 см",
     "Острая салями, перец чили, халапеньо и моцарелла — для любителей жгучего.",
     "26.80", 5, "pizza-diablo.jpg"),
    ("Пицца «Капричоза»", "Пицца", "30 см",
     "Ветчина, грибы, артишоки и маслины с моцареллой — классика итальянской пиццерии.",
     "26.10", 6, "pizza-capricciosa.jpg"),
    ("Пицца «Грибная»", "Пицца", "30 см",
     "Шампиньоны, белые грибы и моцарелла на сливочном соусе — ароматная и мягкая.",
     "24.90", 7, "pizza-mushroom.jpg"),
    ("Пицца «Цезарь»", "Пицца", "30 см",
     "Курица, сыр, сухарики и соус Цезарь на тонком тесте — салат в формате пиццы.",
     "25.90", 8, "pizza-caesar.jpg"),
    ("Пицца «Мясная»", "Пицца", "30 см",
     "Говядина, курица, бекон и пепперони с моцареллой — плотная мясная начинка.",
     "28.50", 9, "pizza-meat.jpg"),
    ("Пицца «Вегетарианская»", "Пицца", "30 см",
     "Перец, томаты, цукини, кукуруза и моцарелла — лёгкая овощная пицца.",
     "23.40", 10, "pizza-veggie.jpg"),
    ("Пицца «Прошутто»", "Пицца", "30 см",
     "Пармская ветчина, руккола и пармезан на моцарелле — после выпечки, чтобы сохранить нежность.",
     "29.20", 11, "pizza-prosciutto.jpg"),
    ("Пицца «Барбекю»", "Пицца", "30 см",
     "Курица, соус барбекю, красный лук и моцарелла — дымный сладковатый вкус.",
     "26.50", 12, "pizza-bbq.jpg"),
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
            help="Привязать фото блюд заново из media/menu (без копирования файлов)",
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
            details = DISH_DETAILS.get(name, {})
            defaults = {
                "category": category,
                "portion": portion,
                "description": description,
                "ingredients": details.get("ingredients", ""),
                "calories": details.get("calories"),
                "allergens": details.get("allergens", ""),
                "cooking_time": details.get("cooking_time"),
                "recipe": details.get("recipe", ""),
                "price": Decimal(price),
                "sort_order": sort_order,
                "is_available": True,
            }
            item, created = MenuItem.objects.get_or_create(name=name, defaults=defaults)
            if not created and refresh:
                for field, value in defaults.items():
                    setattr(item, field, value)
                item.save()

        if refresh:
            MenuItem.objects.exclude(name__in=keep_item_names).update(is_available=False)

    def _attach_photos(self, force: bool = False):
        if not MENU_PHOTOS.exists():
            self.stdout.write(self.style.WARNING(f"Нет папки с фото: {MENU_PHOTOS}"))
            return

        attached = 0
        for name, _category, _portion, _description, _price, _sort, photo_name in MENU_SEED:
            item = MenuItem.objects.filter(name=name).first()
            if not item:
                continue
            photo_path = MENU_PHOTOS / photo_name
            if not photo_path.exists():
                continue
            relative = f"menu/{photo_name}"
            if item.photo and item.photo.name == relative and not force:
                continue
            if item.photo and not force:
                continue
            # Ссылка на уже лежащий файл — без копирования в media.
            item.photo.name = relative
            item.save(update_fields=["photo"])
            attached += 1
            self.stdout.write(f"Фото: {name} ← {photo_name}")

        if attached:
            self.stdout.write(self.style.SUCCESS(f"Привязано фото: {attached}"))

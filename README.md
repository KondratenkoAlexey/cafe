# Кафе — меню и смена персонала

Веб-приложение на Django 5.2 для кафе: гости смотрят меню и бронируют стол, официанты ведут заказы и брони, повара работают с кухней, администратор правит меню, QR и настройки.

**Стек:** Django, UV, PostgreSQL, Redis, Gunicorn, nginx, Docker.  
**Целевая среда:** Raspberry Pi 4 (arm64) в локальной сети кафе.

Репозиторий: https://github.com/KondratenkoAlexey/cafe

## Возможности

- Публичное меню по категориям (цены в BYN, фото, состав, калории, аллергены)
- Бронирование стола гостем (`/reserve/`) и управление бронями у персонала
- Заказы по столам: кухня → подано → счёт / чек (НДС 20%) → оплата
- Рецепт блюда для повара, стоп-лист для админа
- QR-код входа на сайт с редактируемым адресом (`/staff/qr/`)

## Роли

| Логин (после seed) | Роль | Возможности |
|---|---|---|
| `admin` | Администратор | Меню, столы, сотрудники, QR, брони, заказы |
| `waiter` | Официант | Столы, заказы, счёт/чек, брони |
| `cook` | Повар | Очередь кухни, рецепт |

Пароли задаются в `.env` (`SEED_*_PASSWORD`). После первого запуска смените их.

## Архитектура

| Сервис | Назначение |
|---|---|
| `nginx` | Единственный порт наружу: **80** |
| `web` | Django + Gunicorn |
| `db` | PostgreSQL 16 (только внутри Compose) |
| `redis` | Кэш меню (только внутри Compose) |

При старте `web` (`deploy/entrypoint.sh`) выполняет `migrate`, `collectstatic` и `seed_cafe`.

Каталог `deploy/`:

- `nginx.conf` — конфиг nginx
- `entrypoint.sh` — старт контейнера `web`
- `deploy-pi.sh` — короткий запуск стека на Pi

### Медиа

Фото блюд лежат в одной папке: `media/menu/`. Seed и загрузки админки используют её же (`upload_to="menu/"`).

Фото в git не коммитятся (`media/*`, кроме `media/.gitkeep`). На сервере они живут в bind-mount `./media`.

## Локальный запуск (Docker)

```bash
cp .env.example .env
# отредактируйте SECRET_KEY, пароли БД и SEED_*_PASSWORD
docker compose up -d --build
```

Откройте http://localhost/

```bash
docker compose exec web pytest -q
docker compose logs -f web
docker compose exec web python manage.py seed_cafe
```

UV на ПК нужен для зависимостей и IDE (`uv sync`); сайт и БД работают через Compose.

## Переменные окружения

Смотрите `.env.example`. Важно:

| Переменная | Смысл |
|---|---|
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | IP/хосты, с которых открывают сайт (например `192.168.1.104` и `192.168.1.85`) |
| `PUBLIC_BASE_URL` | Адрес по умолчанию в QR; на `/staff/qr/` его можно сменить без правки `.env` |
| `POSTGRES_PASSWORD` | Должен совпадать с паролем в `DATABASE_URL` |
| `SEED_*_PASSWORD` | Пароли учёток после seed |

## Развёртывание на Raspberry Pi

- SSH: `ssh home-server@192.168.1.104`
- Каталог: `/home/home-server/cafe`
- Сайт: http://192.168.1.104/

### 1. Подготовка Pi

```bash
ssh home-server@192.168.1.104
uname -m          # ожидается aarch64
docker --version
docker compose version
```

Если Docker ещё нет (Raspberry Pi OS 64-bit):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker home-server
# выйдите из SSH и зайдите снова
```

### 2. Код на Pi

```bash
cd /home/home-server
git clone https://github.com/KondratenkoAlexey/cafe.git cafe
cd cafe
cp .env.example .env
nano .env
```

В `.env` укажите `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` и `PUBLIC_BASE_URL` под IP Pi. Скопируйте `media/menu/` (или весь `media`), если фото нужны сразу после seed.

Альтернатива без Git — скопировать проект с ПК:

```powershell
scp -r C:\Users\user\Documents\Cafe home-server@192.168.1.104:/home/home-server/cafe
```

### 3. Сборка и запуск

Сборку делайте **на Pi** (образ arm64):

```bash
cd /home/home-server/cafe
docker compose up -d --build
# или: sh deploy/deploy-pi.sh
docker compose ps
docker compose logs web --tail 50
```

### 4. Проверка

1. Гость: меню `/`, бронь `/reserve/`, цены и фото видны.
2. Официант: `waiter` → столы → заказ → «На кухню»; брони в «Брони».
3. Повар: `cook` → кухня → «Готовится» → «Готово» (рецепт по кнопке).
4. Официант: «Подано» → «Счёт» → оплата → чек; стол свободен.
5. Админ: «Блюда» (стоп-лист), «QR» (адрес для гостей), «Настройки».

### 5. Обновление

```bash
ssh home-server@192.168.1.104
cd /home/home-server/cafe
git pull
docker compose up -d --build
```

### Полезные команды

```bash
docker compose logs -f
docker compose logs -f web
docker compose restart web
docker compose down          # данные БД в volume сохраняются
docker compose down -v       # удалить и данные БД
```

## Экраны

| URL | Кто | Назначение |
|---|---|---|
| `/` | Гость | Меню по категориям |
| `/reserve/` | Гость | Бронирование стола |
| `/staff/login/` | Персонал | Вход |
| `/staff/tables/` | Официант | Столы и заказы |
| `/staff/reservations/` | Официант | Брони |
| `/staff/kitchen/` | Повар | Очередь кухни |
| `/staff/menu/dishes/` | Админ | Блюда |
| `/staff/menu/categories/` | Админ | Категории |
| `/staff/settings/tables/` | Админ | Столы зала |
| `/staff/settings/users/` | Админ | Сотрудники |
| `/staff/qr/` | Админ | QR входа на сайт |

# Кафе — меню и смена персонала

Веб-приложение на Django 5.2 для кафе: гости смотрят меню, официанты ведут столы и заказы, повара работают с очередью кухни, администратор редактирует меню и настройки.

Стек: Django, UV, PostgreSQL, Redis, Gunicorn, nginx, Docker. Предназначено для Raspberry Pi 4 в локальной сети кафе.

## Роли

| Логин (после seed) | Роль | Возможности |
|---|---|---|
| `admin` | Администратор | Всё + меню, столы, сотрудники |
| `waiter` | Официант | Столы, заказы, «подано», «оплачено» |
| `cook` | Повар | Очередь кухни |

Пароли задаются в `.env` (`SEED_*_PASSWORD`). После первого запуска смените их.

## Запись проекта в GitHub

Репозиторий в GitHub уже создан. Локально git инициализирован, но **коммитов ещё нет**, remote не привязан. Файл `.env` в git не попадёт (он в `.gitignore`) — так и нужно.

На Windows в PowerShell из каталога проекта:

```powershell
cd C:\Users\user\Documents\Cafe

# 1. Первый коммит
git add .
git status
git commit -m "Initial cafe app: Django menu, staff orders, Docker stack"

# 2. Привязать GitHub (подставьте свой URL)
git remote add origin https://github.com/ВАШ_ЛОГИН/ВАШ_РЕПО.git
# или по SSH:
# git remote add origin git@github.com:ВАШ_ЛОГИН/ВАШ_РЕПО.git

# 3. Отправить код
git branch -M main
git push -u origin main
```

Если GitHub при создании репозитория уже положил `README` или `.gitignore`, перед `push` сделайте:

```powershell
git pull origin main --rebase
git push -u origin main
```

Авторизацию GitHub на Windows удобно делать через Git Credential Manager или SSH-ключ.

После успешного `push` пароль от Raspberry Pi и содержимое `.env` в репозиторий не кладите.

## Локальный запуск (Docker)

```bash
cp .env.example .env
# отредактируйте пароли и SECRET_KEY
docker compose up -d --build
```

Откройте http://localhost/

## Разработка без Docker

```bash
uv sync
# SQLite для быстрых тестов:
set DATABASE_URL=sqlite:///db.sqlite3
uv run python manage.py migrate
uv run python manage.py seed_cafe
uv run python manage.py runserver
uv run pytest
```

## Развёртывание на Raspberry Pi

Целевой сервер:

- SSH: `ssh home-server@192.168.1.104`
- Каталог на сервере: `/home/home-server/cafe`
- Адрес в браузере: http://192.168.1.104/

С компьютера агента сейчас до Pi достучаться не удалось (`Permission denied` / `WinError 10013` на порт 22). Инструкция ниже рассчитана на запуск **с машины, где SSH до Pi уже работает**, либо прямо на самом Pi.

### 1. Подготовка Pi

Подключитесь:

```bash
ssh home-server@192.168.1.104
```

Проверьте архитектуру и Docker:

```bash
uname -m
# ожидается: aarch64

docker --version
docker compose version
```

Если Docker не установлен (Raspberry Pi OS 64-bit):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker home-server
# выйдите из SSH и зайдите снова, чтобы группа docker применилась
```

### 2. Получить код на Pi

**Вариант A — клон с GitHub (предпочтительно):**

```bash
cd /home/home-server
git clone https://github.com/ВАШ_ЛОГИН/ВАШ_РЕПО.git cafe
cd cafe
```

**Вариант B — копирование с ПК (если GitHub ещё не готов):**

С Windows (в PowerShell, когда SSH доступен):

```powershell
scp -r C:\Users\user\Documents\Cafe home-server@192.168.1.104:/home/home-server/cafe
```

На Pi затем удалите лишнее, если скопировалось:

```bash
cd /home/home-server/cafe
rm -rf .venv __pycache__ db.sqlite3 staticfiles
```

### 3. Создать `.env` на сервере

```bash
cd /home/home-server/cafe
cp .env.example .env
nano .env
```

Минимальный рабочий пример:

```env
DEBUG=0
SECRET_KEY=замените-на-длинную-случайную-строку
ALLOWED_HOSTS=192.168.1.104,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.1.104

POSTGRES_DB=cafe
POSTGRES_USER=cafe
POSTGRES_PASSWORD=замените-пароль-бд
DATABASE_URL=postgres://cafe:замените-пароль-бд@db:5432/cafe

REDIS_URL=redis://redis:6379/1

SEED_ADMIN_PASSWORD=замените
SEED_WAITER_PASSWORD=замените
SEED_COOK_PASSWORD=замените
```

`POSTGRES_PASSWORD` и пароль в `DATABASE_URL` должны совпадать.

### 4. Сборка и запуск

Сборку делайте **на самом Pi**, чтобы образ был arm64:

```bash
cd /home/home-server/cafe
docker compose up -d --build
docker compose ps
docker compose logs web --tail 50
```

При старте контейнер `web` сам выполнит `migrate`, `collectstatic` и `seed_cafe`.

Откройте с телефона или ноутбука в Wi‑Fi кафе: http://192.168.1.104/

### 5. Проверка после запуска

1. Гость: меню на `/`, категории и цены видны.
2. Официант: вход `waiter` / пароль из `.env` → столы → открыть заказ → добавить блюдо → «На кухню».
3. Повар: вход `cook` → кухня → «Готовится» → «Готово».
4. Официант: «Подано» → «Оплачено», стол снова свободен.
5. Админ: вход `admin` → «Блюда» → стоп-лист → на публичном меню появляется «закончилось».

### 6. Обновление с GitHub

```bash
ssh home-server@192.168.1.104
cd /home/home-server/cafe
git pull
docker compose up -d --build
```

### Полезные команды

```bash
docker compose logs -f          # все логи
docker compose logs -f web      # только Django
docker compose restart web
docker compose down             # остановить стек (данные БД в volume сохранятся)
docker compose down -v          # остановить и удалить данные БД — осторожно
```

Наружу публикуется только порт **80** (nginx). PostgreSQL и Redis в локальную сеть не пробрасываются.

## Экраны

- `/` — публичное меню
- `/staff/login/` — вход персонала
- `/staff/tables/` — столы официанта
- `/staff/kitchen/` — очередь кухни
- `/staff/menu/` — редактирование меню (админ)
- `/staff/settings/` — столы и сотрудники (админ)

from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import admin_required, cook_required, staff_required, waiter_required
from accounts.models import User
from menu.models import Category, MenuItem

from .models import DiningTable, Order, OrderItem, Receipt, Reservation
from .orders import (
    OrderError,
    add_item_to_order,
    cancel_order,
    cancel_order_item,
    get_or_create_open_order,
    kitchen_queue_queryset,
    mark_order_paid,
    mark_order_served,
    send_order_to_kitchen,
    set_item_cooking,
    set_item_ready,
)
from .qrcode_utils import QR_PRESETS, build_qr_png, get_qr_payload, set_qr_payload
from .reservations import (
    ReservationError,
    create_reservation,
    reservations_for_table_soon,
    set_reservation_status,
    upcoming_reservations_queryset,
)


def _parse_starts_at(value: str):
    value = (value or "").strip()
    if not value:
        raise ReservationError("Укажите дату и время.")
    parsed = parse_datetime(value.replace("T", " ", 1))
    if parsed is None:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        except ValueError as exc:
            raise ReservationError("Некорректная дата или время.") from exc
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _reservation_form_context(extra=None):
    context = {
        "tables": DiningTable.objects.filter(is_active=True).order_by("number"),
        "durations": [60, 90, 120, 150, 180],
    }
    if extra:
        context.update(extra)
    return context


def _menu_manage_url(category_id=None):
    url = reverse("staff_menu_manage")
    if category_id:
        return f"{url}?open={category_id}"
    return url


def staff_login(request):
    if request.user.is_authenticated:
        return redirect("staff_home")

    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect("staff_home")
        error = "Неверный логин или пароль."

    return render(request, "staff/login.html", {"error": error})


@login_required
def staff_logout(request):
    logout(request)
    return redirect("public_menu")


@staff_required
def staff_home(request):
    user = request.user
    if user.is_cook_role and not user.is_waiter_role and not user.is_admin_role:
        return redirect("staff_kitchen")
    if user.is_waiter_role or user.is_admin_role:
        return redirect("staff_tables")
    return redirect("staff_kitchen")


@waiter_required
def staff_tables(request):
    tables = list(
        DiningTable.objects.filter(is_active=True)
        .prefetch_related("orders", "reservations")
        .order_by("number")
    )
    for table in tables:
        table.soon_reservations = reservations_for_table_soon(table)
    return render(request, "staff/tables.html", {"tables": tables})


def public_reservation(request):
    form = {
        "guest_name": "",
        "phone": "",
        "party_size": "2",
        "starts_at": "",
        "duration_minutes": "90",
        "table_id": "",
        "note": "",
    }
    if request.method == "POST":
        form = {key: request.POST.get(key, "").strip() for key in form}
        try:
            table = None
            if form["table_id"]:
                table = get_object_or_404(DiningTable, pk=form["table_id"], is_active=True)
            reservation = create_reservation(
                guest_name=form["guest_name"],
                phone=form["phone"],
                party_size=int(form["party_size"] or 0),
                starts_at=_parse_starts_at(form["starts_at"]),
                duration_minutes=int(form["duration_minutes"] or 90),
                table=table,
                note=form["note"],
                status=Reservation.Status.PENDING,
            )
            messages.success(
                request,
                f"Заявка принята: стол {reservation.table.number} на "
                f"{timezone.localtime(reservation.starts_at):%d.%m.%Y %H:%M}. "
                "Мы подтвердим бронь по телефону.",
            )
            return redirect("public_reservation")
        except (ReservationError, ValueError) as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            messages.error(request, message)

    return render(
        request,
        "service/reservation_public.html",
        _reservation_form_context({"form": form}),
    )


@waiter_required
def staff_reservations(request):
    reservations = upcoming_reservations_queryset()
    form = {
        "guest_name": "",
        "phone": "",
        "party_size": "2",
        "starts_at": "",
        "duration_minutes": "90",
        "table_id": "",
        "note": "",
        "status": Reservation.Status.CONFIRMED,
    }
    return render(
        request,
        "staff/reservations.html",
        _reservation_form_context(
            {
                "reservations": reservations,
                "form": form,
                "statuses": Reservation.Status.choices,
            }
        ),
    )


@waiter_required
@require_POST
def staff_reservation_create(request):
    table = None
    table_id = request.POST.get("table_id", "").strip()
    try:
        if table_id:
            table = get_object_or_404(DiningTable, pk=table_id, is_active=True)
        reservation = create_reservation(
            guest_name=request.POST.get("guest_name", ""),
            phone=request.POST.get("phone", ""),
            party_size=int(request.POST.get("party_size") or 0),
            starts_at=_parse_starts_at(request.POST.get("starts_at", "")),
            duration_minutes=int(request.POST.get("duration_minutes") or 90),
            table=table,
            note=request.POST.get("note", ""),
            created_by=request.user,
            status=request.POST.get("status") or Reservation.Status.CONFIRMED,
        )
        messages.success(
            request,
            f"Бронь создана: {reservation.guest_name}, стол {reservation.table.number}.",
        )
    except (ReservationError, ValueError) as exc:
        message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, message)
    return redirect("staff_reservations")


@waiter_required
@require_POST
def staff_reservation_status(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    status = request.POST.get("status", "").strip()
    try:
        reservation = set_reservation_status(reservation=reservation, status=status)
        messages.success(request, f"Статус брони: {reservation.get_status_display()}.")
    except ReservationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_reservations")


@waiter_required
def staff_table_detail(request, table_id):
    table = get_object_or_404(DiningTable, pk=table_id, is_active=True)
    order = table.open_order
    available_items = (
        MenuItem.objects.filter(is_available=True, category__is_active=True)
        .select_related("category")
        .order_by("category__sort_order", "sort_order", "name")
    )
    return render(
        request,
        "staff/table_detail.html",
        {
            "table": table,
            "order": order,
            "available_items": available_items,
        },
    )


@waiter_required
@require_POST
def staff_open_order(request, table_id):
    table = get_object_or_404(DiningTable, pk=table_id, is_active=True)
    order = get_or_create_open_order(table=table, waiter=request.user)
    return redirect("staff_table_detail", table_id=order.table_id)


@waiter_required
@require_POST
def staff_add_item(request, table_id):
    table = get_object_or_404(DiningTable, pk=table_id, is_active=True)
    order = get_or_create_open_order(table=table, waiter=request.user)
    menu_item = get_object_or_404(MenuItem, pk=request.POST.get("menu_item_id"))
    try:
        quantity = int(request.POST.get("quantity", "1"))
    except ValueError:
        quantity = 1
    note = request.POST.get("note", "")
    try:
        add_item_to_order(order=order, menu_item=menu_item, quantity=quantity, note=note)
        messages.success(request, f"Добавлено: {menu_item.name}")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_table_detail", table_id=table.id)


@waiter_required
@require_POST
def staff_send_kitchen(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    try:
        send_order_to_kitchen(order=order)
        messages.success(request, "Заказ отправлен на кухню.")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_table_detail", table_id=order.table_id)


@waiter_required
@require_POST
def staff_mark_served(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    try:
        mark_order_served(order=order)
        messages.success(request, "Заказ отмечен как поданный.")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_table_detail", table_id=order.table_id)


@waiter_required
def staff_bill(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("table", "waiter").prefetch_related("items__menu_item"),
        pk=order_id,
    )
    if order.status != Order.Status.SERVED:
        messages.error(request, "Счёт можно показать только для поданного заказа.")
        return redirect("staff_table_detail", table_id=order.table_id)
    items = [item for item in order.items.all() if item.status != OrderItem.Status.CANCELLED]
    return render(
        request,
        "staff/bill.html",
        {"order": order, "table": order.table, "items": items},
    )


@waiter_required
@require_POST
def staff_mark_paid(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    payment_method = request.POST.get("payment_method", "").strip()
    try:
        _order, receipt = mark_order_paid(order=order, payment_method=payment_method)
        messages.success(request, f"Заказ оплачен. Чек {receipt.number}.")
        return redirect("staff_receipt", receipt_id=receipt.id)
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("staff_table_detail", table_id=order.table_id)


@waiter_required
def staff_receipt(request, receipt_id):
    receipt = get_object_or_404(
        Receipt.objects.select_related("order", "order__table").prefetch_related("lines"),
        pk=receipt_id,
    )
    return render(request, "staff/receipt.html", {"receipt": receipt})


@waiter_required
@require_POST
def staff_cancel_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    try:
        cancel_order(order=order)
        messages.success(request, "Заказ отменён.")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_tables")


@waiter_required
@require_POST
def staff_cancel_item(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    table_id = item.order.table_id
    try:
        cancel_order_item(item=item)
        messages.success(request, "Позиция отменена.")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_table_detail", table_id=table_id)


@cook_required
def staff_kitchen(request):
    items = kitchen_queue_queryset()
    partial = request.headers.get("HX-Request") == "true"
    template = "staff/partials/kitchen_queue.html" if partial else "staff/kitchen.html"
    return render(request, template, {"items": items})


@cook_required
def staff_recipe(request, item_id):
    item = get_object_or_404(
        OrderItem.objects.select_related("menu_item", "order", "order__table"),
        pk=item_id,
    )
    return render(request, "staff/recipe.html", {"item": item, "dish": item.menu_item})


@cook_required
@require_POST
def staff_item_cooking(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    try:
        set_item_cooking(item=item)
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "staff/partials/kitchen_queue.html",
            {"items": kitchen_queue_queryset()},
        )
    return redirect("staff_kitchen")


@cook_required
@require_POST
def staff_item_ready(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    try:
        set_item_ready(item=item)
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "staff/partials/kitchen_queue.html",
            {"items": kitchen_queue_queryset()},
        )
    return redirect("staff_kitchen")


@admin_required
def staff_menu_manage(request):
    categories = Category.objects.prefetch_related("items").order_by("sort_order", "name")
    open_category = request.GET.get("open")
    return render(
        request,
        "staff/menu_manage.html",
        {"categories": categories, "open_category": open_category},
    )


@admin_required
@require_POST
def staff_category_save(request):
    category_id = request.POST.get("category_id")
    name = request.POST.get("name", "").strip()
    sort_order = int(request.POST.get("sort_order") or 0)
    is_active = request.POST.get("is_active") == "on"
    if not name:
        messages.error(request, "Укажите название категории.")
        return redirect("staff_menu_manage")

    if category_id:
        category = get_object_or_404(Category, pk=category_id)
        category.name = name
        category.sort_order = sort_order
        category.is_active = is_active
        category.save()
        messages.success(request, "Категория обновлена.")
        return redirect(_menu_manage_url(category.id))

    category = Category.objects.create(name=name, sort_order=sort_order, is_active=is_active)
    messages.success(request, "Категория создана.")
    return redirect(_menu_manage_url(category.id))


@admin_required
@require_POST
def staff_item_save(request):
    item_id = request.POST.get("item_id")
    name = request.POST.get("name", "").strip()
    category = get_object_or_404(Category, pk=request.POST.get("category_id"))
    description = request.POST.get("description", "").strip()
    price = request.POST.get("price", "0").replace(",", ".")
    sort_order = int(request.POST.get("sort_order") or 0)
    is_available = request.POST.get("is_available") == "on"
    photo = request.FILES.get("photo")

    if not name:
        messages.error(request, "Укажите название блюда.")
        return redirect(_menu_manage_url(category.id))

    if item_id:
        item = get_object_or_404(MenuItem, pk=item_id)
    else:
        item = MenuItem(category=category)

    item.category = category
    item.name = name
    item.portion = request.POST.get("portion", "").strip()
    item.description = description
    item.ingredients = request.POST.get("ingredients", "").strip()
    item.allergens = request.POST.get("allergens", "").strip()
    item.recipe = request.POST.get("recipe", "").strip()
    calories = request.POST.get("calories", "").strip()
    cooking_time = request.POST.get("cooking_time", "").strip()
    item.calories = int(calories) if calories else None
    item.cooking_time = int(cooking_time) if cooking_time else None
    item.price = price
    item.sort_order = sort_order
    item.is_available = is_available
    if photo:
        item.photo = photo
    item.save()
    messages.success(request, "Блюдо сохранено.")
    return redirect(_menu_manage_url(category.id))


@admin_required
@require_POST
def staff_item_toggle(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    status = "в меню" if item.is_available else "в стоп-листе"
    messages.success(request, f"{item.name}: {status}")
    return redirect(_menu_manage_url(item.category_id))


@admin_required
@require_POST
def staff_item_delete(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    category_id = item.category_id
    name = item.name
    try:
        item.delete()
    except ProtectedError:
        messages.error(
            request,
            f'Нельзя удалить «{name}»: блюдо уже есть в заказах. Снимите его в стоп-лист.',
        )
        return redirect(_menu_manage_url(category_id))
    messages.success(request, f'Блюдо «{name}» удалено.')
    return redirect(_menu_manage_url(category_id))


@admin_required
def staff_settings(request):
    tables = DiningTable.objects.order_by("number")
    users = User.objects.order_by("username")
    return render(
        request,
        "staff/settings.html",
        {"tables": tables, "users": users, "roles": User.Role.choices},
    )


@admin_required
def staff_qr(request):
    payload = get_qr_payload()
    return render(
        request,
        "staff/qr.html",
        {
            "qr_payload": payload,
            "qr_presets": QR_PRESETS,
            "qr_image_url": reverse("staff_qr_image"),
        },
    )


@admin_required
@require_POST
def staff_qr_save(request):
    try:
        payload = set_qr_payload(request.POST.get("qr_payload", ""))
        messages.success(request, f"QR обновлён: {payload}")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("staff_qr")


@admin_required
@require_GET
def staff_qr_image(request):
    payload = request.GET.get("payload")
    if payload:
        try:
            from .qrcode_utils import normalize_qr_payload

            text = normalize_qr_payload(payload)
        except ValueError:
            text = get_qr_payload()
    else:
        text = get_qr_payload()
    png = build_qr_png(text)
    response = HttpResponse(png, content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


@admin_required
@require_POST
def staff_table_save(request):
    table_id = request.POST.get("table_id")
    number = int(request.POST.get("number") or 0)
    seats = int(request.POST.get("seats") or 4)
    is_active = request.POST.get("is_active") == "on"
    if number < 1:
        messages.error(request, "Номер стола должен быть больше 0.")
        return redirect("staff_settings")

    if table_id:
        table = get_object_or_404(DiningTable, pk=table_id)
        table.number = number
        table.seats = seats
        table.is_active = is_active
        table.save()
        messages.success(request, "Стол обновлён.")
    else:
        DiningTable.objects.create(number=number, seats=seats, is_active=is_active)
        messages.success(request, "Стол создан.")
    return redirect("staff_settings")


@admin_required
@require_POST
def staff_table_delete(request, table_id):
    table = get_object_or_404(DiningTable, pk=table_id)
    number = table.number
    try:
        table.delete()
    except ProtectedError:
        messages.error(
            request,
            f"Нельзя удалить стол {number}: по нему есть заказы. Сделайте стол неактивным.",
        )
        return redirect("staff_settings")
    messages.success(request, f"Стол {number} удалён.")
    return redirect("staff_settings")


@admin_required
@require_POST
def staff_user_save(request):
    user_id = request.POST.get("user_id")
    username = request.POST.get("username", "").strip()
    role = request.POST.get("role", User.Role.WAITER)
    password = request.POST.get("password", "")
    first_name = request.POST.get("first_name", "").strip()
    is_active = request.POST.get("is_active") == "on"

    if not username:
        messages.error(request, "Укажите логин.")
        return redirect("staff_settings")

    if user_id:
        user = get_object_or_404(User, pk=user_id)
        user.username = username
        user.role = role
        user.first_name = first_name
        user.is_active = is_active
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, "Сотрудник обновлён.")
    else:
        if not password:
            messages.error(request, "Для нового сотрудника нужен пароль.")
            return redirect("staff_settings")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Такой логин уже занят.")
            return redirect("staff_settings")
        user = User(username=username, role=role, first_name=first_name, is_active=is_active)
        user.set_password(password)
        user.save()
        messages.success(request, "Сотрудник создан.")
    return redirect("staff_settings")


@admin_required
@require_POST
def staff_user_delete(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.user.pk:
        messages.error(request, "Нельзя удалить свою учётную запись.")
        return redirect("staff_settings")
    username = user.username
    try:
        user.delete()
    except ProtectedError:
        messages.error(
            request,
            f"Нельзя удалить «{username}»: сотрудник связан с заказами. Сделайте учётку неактивной.",
        )
        return redirect("staff_settings")
    messages.success(request, f"Сотрудник «{username}» удалён.")
    return redirect("staff_settings")

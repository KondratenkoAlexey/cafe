from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, cook_required, staff_required, waiter_required
from accounts.models import User
from menu.models import Category, MenuItem

from .models import DiningTable, Order, OrderItem
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
    tables = DiningTable.objects.filter(is_active=True).prefetch_related("orders")
    return render(request, "staff/tables.html", {"tables": tables})


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
@require_POST
def staff_mark_paid(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    try:
        mark_order_paid(order=order)
        messages.success(request, "Заказ оплачен, стол свободен.")
    except OrderError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("staff_tables")


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
    return render(request, "staff/menu_manage.html", {"categories": categories})


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
    else:
        Category.objects.create(name=name, sort_order=sort_order, is_active=is_active)
        messages.success(request, "Категория создана.")
    return redirect("staff_menu_manage")


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
        return redirect("staff_menu_manage")

    if item_id:
        item = get_object_or_404(MenuItem, pk=item_id)
    else:
        item = MenuItem(category=category)

    item.category = category
    item.name = name
    item.description = description
    item.price = price
    item.sort_order = sort_order
    item.is_available = is_available
    if photo:
        item.photo = photo
    item.save()
    messages.success(request, "Блюдо сохранено.")
    return redirect("staff_menu_manage")


@admin_required
@require_POST
def staff_item_toggle(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    status = "в меню" if item.is_available else "в стоп-листе"
    messages.success(request, f"{item.name}: {status}")
    return redirect("staff_menu_manage")


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

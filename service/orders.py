"""Правила смены статусов заказов и позиций."""

from django.core.exceptions import ValidationError
from django.db import transaction
from menu.models import MenuItem

from .models import Order, OrderItem


class OrderError(ValidationError):
    pass


@transaction.atomic
def get_or_create_open_order(*, table, waiter) -> Order:
    order = (
        Order.objects.select_for_update()
        .filter(table=table)
        .exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])
        .first()
    )
    if order:
        return order
    return Order.objects.create(table=table, waiter=waiter)


@transaction.atomic
def add_item_to_order(*, order: Order, menu_item: MenuItem, quantity: int = 1, note: str = "") -> OrderItem:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_add_items():
        raise OrderError("В этот заказ больше нельзя добавлять блюда.")
    if not menu_item.is_available:
        raise OrderError("Блюдо сейчас в стоп-листе.")
    if quantity < 1:
        raise OrderError("Количество должно быть не меньше 1.")

    return OrderItem.objects.create(
        order=order,
        menu_item=menu_item,
        quantity=quantity,
        unit_price=menu_item.price,
        note=note.strip(),
        status=OrderItem.Status.DRAFT,
    )


@transaction.atomic
def send_order_to_kitchen(*, order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    draft_items = list(order.items.select_for_update().filter(status=OrderItem.Status.DRAFT))
    if not draft_items:
        raise OrderError("Нет новых позиций для отправки на кухню.")

    for item in draft_items:
        if not item.menu_item.is_available:
            raise OrderError(f"Блюдо «{item.menu_item.name}» в стоп-листе.")
        item.status = OrderItem.Status.QUEUED
        item.save(update_fields=["status", "updated_at"])

    order.status = Order.Status.IN_KITCHEN
    order.save(update_fields=["status", "updated_at"])
    return order


def _refresh_order_status(order: Order) -> None:
    active = order.items.exclude(status=OrderItem.Status.CANCELLED)
    if not active.exists():
        return

    kitchen_statuses = {
        OrderItem.Status.QUEUED,
        OrderItem.Status.COOKING,
        OrderItem.Status.READY,
        OrderItem.Status.SERVED,
    }
    sent = active.filter(status__in=kitchen_statuses)
    if not sent.exists():
        if order.status not in {Order.Status.PAID, Order.Status.CANCELLED, Order.Status.SERVED}:
            order.status = Order.Status.DRAFT
            order.save(update_fields=["status", "updated_at"])
        return

    unfinished = sent.filter(
        status__in=[OrderItem.Status.QUEUED, OrderItem.Status.COOKING]
    )
    if unfinished.exists():
        order.status = Order.Status.IN_KITCHEN
    else:
        # Все отправленные позиции готовы или уже поданы.
        if order.status in {Order.Status.IN_KITCHEN, Order.Status.READY, Order.Status.DRAFT}:
            order.status = Order.Status.READY
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def set_item_cooking(*, item: OrderItem) -> OrderItem:
    item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
    if item.status != OrderItem.Status.QUEUED:
        raise OrderError("Готовить можно только позиции из очереди.")
    item.status = OrderItem.Status.COOKING
    item.save(update_fields=["status", "updated_at"])
    _refresh_order_status(item.order)
    return item


@transaction.atomic
def set_item_ready(*, item: OrderItem) -> OrderItem:
    item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
    if item.status not in {OrderItem.Status.QUEUED, OrderItem.Status.COOKING}:
        raise OrderError("Отметить готовым можно позицию в очереди или в готовке.")
    item.status = OrderItem.Status.READY
    item.save(update_fields=["status", "updated_at"])
    _refresh_order_status(item.order)
    return item


@transaction.atomic
def mark_order_served(*, order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_mark_served():
        raise OrderError("Подать можно только готовый заказ.")

    order.items.filter(status=OrderItem.Status.READY).update(status=OrderItem.Status.SERVED)
    order.status = Order.Status.SERVED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def mark_order_paid(*, order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_mark_paid():
        raise OrderError("Оплатить можно только поданный заказ.")
    order.status = Order.Status.PAID
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order(*, order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_cancel():
        raise OrderError("Этот заказ нельзя отменить.")
    order.items.exclude(
        status__in=[OrderItem.Status.SERVED, OrderItem.Status.CANCELLED]
    ).update(status=OrderItem.Status.CANCELLED)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order_item(*, item: OrderItem) -> OrderItem:
    item = OrderItem.objects.select_for_update().select_related("order").get(pk=item.pk)
    if item.order.status in {Order.Status.PAID, Order.Status.CANCELLED}:
        raise OrderError("Позицию закрытого заказа нельзя отменить.")
    if item.status == OrderItem.Status.SERVED:
        raise OrderError("Поданную позицию нельзя отменить.")
    item.status = OrderItem.Status.CANCELLED
    item.save(update_fields=["status", "updated_at"])
    _refresh_order_status(item.order)
    return item


def kitchen_queue_queryset():
    return (
        OrderItem.objects.filter(
            status__in=[OrderItem.Status.QUEUED, OrderItem.Status.COOKING]
        )
        .select_related("order", "order__table", "menu_item")
        .order_by("created_at")
    )

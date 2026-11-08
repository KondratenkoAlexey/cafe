"""Правила смены статусов заказов и позиций."""

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from menu.models import MenuItem

from .models import Order, OrderItem, Receipt, ReceiptLine


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
def mark_order_paid(*, order: Order, payment_method: str) -> tuple[Order, Receipt]:
    order = (
        Order.objects.select_for_update()
        .select_related("table", "waiter")
        .prefetch_related("items")
        .get(pk=order.pk)
    )
    if not order.can_mark_paid():
        raise OrderError("Оплатить можно только поданный заказ.")
    if payment_method not in Receipt.PaymentMethod.values:
        raise OrderError("Укажите способ оплаты: наличные или карта.")
    if hasattr(order, "receipt"):
        raise OrderError("Чек по этому заказу уже создан.")

    lines = [
        item
        for item in order.items.all()
        if item.status != OrderItem.Status.CANCELLED
    ]
    if not lines:
        raise OrderError("Нельзя оплатить пустой заказ.")

    total = order.total
    vat_rate = Decimal(str(settings.VAT_RATE))
    vat_amount = (total * vat_rate / (Decimal("1") + vat_rate)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    paid_at = timezone.now()
    number = f"C-{paid_at.strftime('%Y%m%d')}-{order.pk:05d}"

    order.status = Order.Status.PAID
    order.save(update_fields=["status", "updated_at"])

    receipt = Receipt.objects.create(
        order=order,
        number=number,
        table_number=order.table.number,
        waiter_name=order.waiter.get_full_name() or order.waiter.username,
        payment_method=payment_method,
        total=total,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        paid_at=paid_at,
    )
    ReceiptLine.objects.bulk_create(
        [
            ReceiptLine(
                receipt=receipt,
                name=item.menu_item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                sort_order=index,
            )
            for index, item in enumerate(lines)
        ]
    )
    return order, receipt


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

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from menu.models import MenuItem


class DiningTable(models.Model):
    number = models.PositiveIntegerField("Номер", unique=True)
    seats = models.PositiveIntegerField("Мест", default=4)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "Стол"
        verbose_name_plural = "Столы"

    def __str__(self) -> str:
        return f"Стол {self.number}"

    @property
    def open_order(self):
        return (
            self.orders.exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])
            .order_by("-created_at")
            .first()
        )

    @property
    def is_occupied(self) -> bool:
        return self.open_order is not None


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        IN_KITCHEN = "in_kitchen", "На кухне"
        READY = "ready", "Готов"
        SERVED = "served", "Подан"
        PAID = "paid", "Оплачен"
        CANCELLED = "cancelled", "Отменён"

    table = models.ForeignKey(
        DiningTable,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Стол",
    )
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Официант",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )
    created_at = models.DateTimeField("Создан", default=timezone.now)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        constraints = [
            models.UniqueConstraint(
                fields=["table"],
                condition=~Q(status__in=["paid", "cancelled"]),
                name="unique_open_order_per_table",
            )
        ]

    def __str__(self) -> str:
        return f"Заказ #{self.pk} · стол {self.table.number}"

    @property
    def total(self) -> Decimal:
        result = self.items.exclude(status=OrderItem.Status.CANCELLED).aggregate(
            total=Sum(models.F("unit_price") * models.F("quantity"), output_field=models.DecimalField())
        )["total"]
        return result or Decimal("0.00")

    def can_add_items(self) -> bool:
        return self.status not in {self.Status.PAID, self.Status.CANCELLED}

    def can_send_to_kitchen(self) -> bool:
        return self.can_add_items() and self.items.filter(status=OrderItem.Status.DRAFT).exists()

    def can_mark_served(self) -> bool:
        return self.status == self.Status.READY

    def can_mark_paid(self) -> bool:
        return self.status == self.Status.SERVED

    def can_cancel(self) -> bool:
        return self.status not in {self.Status.PAID, self.Status.CANCELLED}


class OrderItem(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        QUEUED = "queued", "В очереди"
        COOKING = "cooking", "Готовится"
        READY = "ready", "Готово"
        SERVED = "served", "Подано"
        CANCELLED = "cancelled", "Отменено"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Блюдо",
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    unit_price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    note = models.CharField("Комментарий", max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )
    created_at = models.DateTimeField("Создан", default=timezone.now)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self) -> str:
        return f"{self.menu_item.name} × {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def clean(self):
        if self.menu_item_id and not self.menu_item.is_available and self.status == self.Status.DRAFT:
            raise ValidationError({"menu_item": "Блюдо сейчас в стоп-листе."})

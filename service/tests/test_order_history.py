from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from menu.models import Category, MenuItem
from service.models import DiningTable, Order, OrderItem
from service.orders import (
    add_item_to_order,
    mark_order_paid,
    mark_order_served,
    send_order_to_kitchen,
    set_item_cooking,
    set_item_ready,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="hist-admin",
        password="pass",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def paid_order(admin_user):
    table = DiningTable.objects.create(number=42, seats=4)
    category = Category.objects.create(name="Тест", sort_order=1)
    dish = MenuItem.objects.create(
        category=category,
        name="Тест-блюдо",
        price=Decimal("10.00"),
        is_available=True,
    )
    order = Order.objects.create(table=table, waiter=admin_user)
    item = add_item_to_order(order=order, menu_item=dish, quantity=2)
    send_order_to_kitchen(order=order)
    set_item_cooking(item=item)
    set_item_ready(item=item)
    mark_order_served(order=order)
    order, receipt = mark_order_paid(order=order, payment_method="cash")
    return order, receipt


def test_admin_sees_history_total(admin_user, paid_order):
    _order, receipt = paid_order
    client = Client()
    client.force_login(admin_user)
    day = timezone.localtime(receipt.paid_at).date().isoformat()
    response = client.get(
        reverse("staff_order_history"),
        {"date_from": day, "date_to": day},
    )
    assert response.status_code == 200
    assert response.context["orders_count"] == 1
    assert response.context["total_sum"] == Decimal("20.00")
    assert receipt.number.encode() in response.content

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from accounts.models import User
from menu.models import MENU_CACHE_KEY, Category, MenuItem
from service.models import DiningTable, Order, OrderItem
from service.orders import (
    OrderError,
    add_item_to_order,
    mark_order_paid,
    mark_order_served,
    send_order_to_kitchen,
    set_item_cooking,
    set_item_ready,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def waiter(db):
    return User.objects.create_user(username="w1", password="pass", role=User.Role.WAITER)


@pytest.fixture
def cook(db):
    return User.objects.create_user(username="c1", password="pass", role=User.Role.COOK)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="a1",
        password="pass",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def table(db):
    return DiningTable.objects.create(number=1, seats=4)


@pytest.fixture
def latte(db):
    category = Category.objects.create(name="Напитки", sort_order=1)
    return MenuItem.objects.create(
        category=category,
        name="Латте",
        price=Decimal("9.10"),
        is_available=True,
    )


def test_cannot_add_stopped_item(waiter, table, latte):
    latte.is_available = False
    latte.save()
    order = Order.objects.create(table=table, waiter=waiter)
    with pytest.raises(OrderError):
        add_item_to_order(order=order, menu_item=latte, quantity=1)


def test_order_status_flow(waiter, table, latte):
    order = Order.objects.create(table=table, waiter=waiter)
    item = add_item_to_order(order=order, menu_item=latte, quantity=2)
    assert item.status == OrderItem.Status.DRAFT

    send_order_to_kitchen(order=order)
    order.refresh_from_db()
    item.refresh_from_db()
    assert order.status == Order.Status.IN_KITCHEN
    assert item.status == OrderItem.Status.QUEUED

    set_item_cooking(item=item)
    item.refresh_from_db()
    assert item.status == OrderItem.Status.COOKING

    set_item_ready(item=item)
    order.refresh_from_db()
    item.refresh_from_db()
    assert item.status == OrderItem.Status.READY
    assert order.status == Order.Status.READY

    mark_order_served(order=order)
    order.refresh_from_db()
    assert order.status == Order.Status.SERVED

    order, receipt = mark_order_paid(order=order, payment_method="cash")
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert table.open_order is None
    assert receipt.number
    assert receipt.lines.count() == 1
    assert receipt.total == order.total


def test_role_access(waiter, cook, admin_user, table):
    client = Client()

    assert client.get(reverse("staff_tables")).status_code == 302

    client.login(username="c1", password="pass")
    assert client.get(reverse("staff_tables")).status_code == 403
    assert client.get(reverse("staff_kitchen")).status_code == 200
    client.logout()

    client.login(username="w1", password="pass")
    assert client.get(reverse("staff_tables")).status_code == 200
    assert client.get(reverse("staff_kitchen")).status_code == 403
    assert client.get(reverse("staff_menu_manage")).status_code == 403
    client.logout()

    client.login(username="a1", password="pass")
    assert client.get(reverse("staff_tables")).status_code == 200
    assert client.get(reverse("staff_kitchen")).status_code == 200
    assert client.get(reverse("staff_menu_manage")).status_code == 200
    assert client.get(reverse("staff_settings_tables")).status_code == 200
    assert client.get(reverse("staff_settings_users")).status_code == 200


def test_menu_cache_invalidation(latte):
    client = Client()
    cache.clear()
    response = client.get(reverse("public_menu"))
    assert response.status_code == 200
    assert cache.get(f"{MENU_CACHE_KEY}:categories") is not None

    latte.name = "Латте большой"
    latte.save()
    assert cache.get(f"{MENU_CACHE_KEY}:categories") is None


def test_category_page(latte):
    client = Client()
    response = client.get(reverse("public_category", args=[latte.category_id]))
    assert response.status_code == 200
    assert latte.name.encode() in response.content or latte.name in response.content.decode()

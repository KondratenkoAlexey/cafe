from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from service.models import DiningTable, Reservation
from service.reservations import ReservationError, create_reservation, set_reservation_status


pytestmark = pytest.mark.django_db


@pytest.fixture
def waiter(db):
    return User.objects.create_user(username="w-res", password="pass", role=User.Role.WAITER)


@pytest.fixture
def table(db):
    return DiningTable.objects.create(number=10, seats=4)


@pytest.fixture
def big_table(db):
    return DiningTable.objects.create(number=11, seats=8)


def _future(**kwargs):
    return timezone.now() + timedelta(**kwargs)


def test_create_reservation_auto_assigns_smallest_table(table, big_table):
    reservation = create_reservation(
        guest_name="Анна",
        phone="+375291112233",
        party_size=3,
        starts_at=_future(hours=2),
    )
    assert reservation.table_id == table.id
    assert reservation.status == Reservation.Status.PENDING


def test_overlap_blocks_same_table(table):
    starts = _future(hours=3)
    create_reservation(
        guest_name="Анна",
        phone="+375291112233",
        party_size=2,
        starts_at=starts,
        table=table,
        status=Reservation.Status.CONFIRMED,
    )
    with pytest.raises(ReservationError):
        create_reservation(
            guest_name="Борис",
            phone="+375291112244",
            party_size=2,
            starts_at=starts + timedelta(minutes=30),
            table=table,
        )


def test_cancelled_does_not_block(table):
    starts = _future(hours=4)
    first = create_reservation(
        guest_name="Анна",
        phone="+375291112233",
        party_size=2,
        starts_at=starts,
        table=table,
        status=Reservation.Status.CONFIRMED,
    )
    set_reservation_status(reservation=first, status=Reservation.Status.CANCELLED)
    second = create_reservation(
        guest_name="Борис",
        phone="+375291112244",
        party_size=2,
        starts_at=starts,
        table=table,
    )
    assert second.table_id == table.id


def test_public_reservation_form(table):
    client = Client()
    starts = timezone.localtime(_future(hours=5)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        reverse("public_reservation"),
        {
            "guest_name": "Гость",
            "phone": "+375291112255",
            "party_size": "2",
            "starts_at": starts,
            "duration_minutes": "90",
            "table_id": str(table.id),
            "note": "",
        },
    )
    assert response.status_code == 302
    assert Reservation.objects.filter(guest_name="Гость", table=table).exists()


def test_staff_can_confirm_reservation(waiter, table):
    reservation = create_reservation(
        guest_name="Анна",
        phone="+375291112233",
        party_size=2,
        starts_at=_future(hours=6),
        table=table,
        status=Reservation.Status.PENDING,
    )
    client = Client()
    client.force_login(waiter)
    response = client.post(
        reverse("staff_reservation_status", args=[reservation.id]),
        {"status": Reservation.Status.CONFIRMED},
    )
    assert response.status_code == 302
    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.CONFIRMED

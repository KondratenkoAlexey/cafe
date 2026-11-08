"""Правила бронирования столов."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import DiningTable, Reservation


class ReservationError(ValidationError):
    pass


ACTIVE_STATUSES = (Reservation.Status.PENDING, Reservation.Status.CONFIRMED)


def reservation_window(starts_at, duration_minutes: int):
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    return starts_at, ends_at


def overlapping_reservations(*, table: DiningTable, starts_at, duration_minutes: int, exclude_id=None):
    starts_at, ends_at = reservation_window(starts_at, duration_minutes)
    qs = Reservation.objects.filter(table=table, status__in=ACTIVE_STATUSES)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return [
        reservation
        for reservation in qs
        if reservation.starts_at < ends_at and reservation.ends_at > starts_at
    ]


def find_available_table(*, party_size: int, starts_at, duration_minutes: int = 90):
    tables = DiningTable.objects.filter(is_active=True, seats__gte=party_size).order_by("seats", "number")
    for table in tables:
        if not overlapping_reservations(
            table=table, starts_at=starts_at, duration_minutes=duration_minutes
        ):
            return table
    return None


@transaction.atomic
def create_reservation(
    *,
    guest_name: str,
    phone: str,
    party_size: int,
    starts_at,
    duration_minutes: int = 90,
    table: DiningTable | None = None,
    note: str = "",
    created_by=None,
    status: str = Reservation.Status.PENDING,
) -> Reservation:
    guest_name = guest_name.strip()
    phone = phone.strip()
    note = note.strip()

    if not guest_name:
        raise ReservationError("Укажите имя гостя.")
    if not phone:
        raise ReservationError("Укажите телефон.")
    if party_size < 1:
        raise ReservationError("Количество гостей должно быть не меньше 1.")
    if duration_minutes < 30:
        raise ReservationError("Минимальная длительность брони — 30 минут.")
    if starts_at < timezone.now() - timedelta(minutes=5):
        raise ReservationError("Нельзя бронировать на прошедшее время.")

    if table is None:
        table = find_available_table(
            party_size=party_size, starts_at=starts_at, duration_minutes=duration_minutes
        )
        if table is None:
            raise ReservationError("На это время нет свободного стола подходящего размера.")
    else:
        if not table.is_active:
            raise ReservationError("Этот стол недоступен.")
        if table.seats < party_size:
            raise ReservationError(f"За столом {table.number} только {table.seats} мест.")
        if overlapping_reservations(
            table=table, starts_at=starts_at, duration_minutes=duration_minutes
        ):
            raise ReservationError(f"Стол {table.number} уже занят на выбранное время.")

    return Reservation.objects.create(
        table=table,
        guest_name=guest_name,
        phone=phone,
        party_size=party_size,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        status=status,
        note=note,
        created_by=created_by,
    )


@transaction.atomic
def set_reservation_status(*, reservation: Reservation, status: str) -> Reservation:
    if status not in Reservation.Status.values:
        raise ReservationError("Неизвестный статус брони.")
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if status in ACTIVE_STATUSES:
        conflicts = overlapping_reservations(
            table=reservation.table,
            starts_at=reservation.starts_at,
            duration_minutes=reservation.duration_minutes,
            exclude_id=reservation.pk,
        )
        if conflicts:
            raise ReservationError("Нельзя подтвердить: стол уже занят другой бронью.")
    reservation.status = status
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


def upcoming_reservations_queryset():
    now = timezone.now()
    return (
        Reservation.objects.filter(status__in=ACTIVE_STATUSES, starts_at__gte=now - timedelta(hours=1))
        .select_related("table", "created_by")
        .order_by("starts_at")
    )


def reservations_for_table_soon(table: DiningTable, within_hours: int = 3):
    now = timezone.now()
    end = now + timedelta(hours=within_hours)
    return [
        reservation
        for reservation in table.reservations.filter(status__in=ACTIVE_STATUSES)
        if reservation.starts_at < end and reservation.ends_at > now
    ]

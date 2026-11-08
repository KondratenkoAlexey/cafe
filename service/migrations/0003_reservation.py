import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("service", "0002_dish_details_and_receipts"),
    ]

    operations = [
        migrations.CreateModel(
            name="Reservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_name", models.CharField(max_length=120, verbose_name="Имя гостя")),
                ("phone", models.CharField(max_length=32, verbose_name="Телефон")),
                ("party_size", models.PositiveIntegerField(default=2, verbose_name="Гостей")),
                ("starts_at", models.DateTimeField(verbose_name="Начало")),
                ("duration_minutes", models.PositiveIntegerField(default=90, verbose_name="Длительность, мин")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает"),
                            ("confirmed", "Подтверждена"),
                            ("cancelled", "Отменена"),
                            ("completed", "Завершена"),
                            ("no_show", "Не пришли"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="Комментарий")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Создана")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлена")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_reservations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Создал",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="service.diningtable",
                        verbose_name="Стол",
                    ),
                ),
            ],
            options={
                "verbose_name": "Бронь",
                "verbose_name_plural": "Брони",
                "ordering": ["starts_at"],
            },
        ),
    ]

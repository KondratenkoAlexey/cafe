from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0003_reservation"),
    ]

    operations = [
        migrations.CreateModel(
            name="CafeSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "qr_payload",
                    models.CharField(
                        blank=True,
                        help_text="Обычно адрес сайта, например http://192.168.1.104/",
                        max_length=500,
                        verbose_name="Текст в QR",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "Настройки кафе",
                "verbose_name_plural": "Настройки кафе",
            },
        ),
    ]

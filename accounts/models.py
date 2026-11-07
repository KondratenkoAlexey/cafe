from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        WAITER = "waiter", "Официант"
        COOK = "cook", "Повар"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WAITER,
        verbose_name="Роль",
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_waiter_role(self) -> bool:
        return self.role in {self.Role.WAITER, self.Role.ADMIN} or self.is_superuser

    @property
    def is_cook_role(self) -> bool:
        return self.role in {self.Role.COOK, self.Role.ADMIN} or self.is_superuser

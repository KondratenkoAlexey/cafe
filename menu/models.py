from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

MENU_CACHE_KEY = "menu:public"


class Category(models.Model):
    name = models.CharField("Название", max_length=100)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Категория",
    )
    name = models.CharField("Название", max_length=150)
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    photo = models.ImageField("Фото", upload_to="menu/", blank=True)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_available = models.BooleanField("В наличии", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"

    def __str__(self) -> str:
        return self.name


def invalidate_menu_cache(**_kwargs) -> None:
    cache.delete(MENU_CACHE_KEY)


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
@receiver(post_save, sender=MenuItem)
@receiver(post_delete, sender=MenuItem)
def clear_menu_cache(sender, **kwargs):
    invalidate_menu_cache()

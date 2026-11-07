from django.core.cache import cache
from django.shortcuts import get_object_or_404, render

from .models import MENU_CACHE_KEY, Category


def public_menu(request):
    """Список категорий — блюда открываются после выбора категории."""
    cache_key = f"{MENU_CACHE_KEY}:categories"
    categories = cache.get(cache_key)
    if categories is None:
        categories = list(
            Category.objects.filter(is_active=True).order_by("sort_order", "name")
        )
        cache.set(cache_key, categories, timeout=300)

    return render(request, "menu/public.html", {"categories": categories})


def public_category(request, category_id: int):
    category = get_object_or_404(Category, pk=category_id, is_active=True)
    cache_key = f"{MENU_CACHE_KEY}:category:{category_id}"
    items = cache.get(cache_key)
    if items is None:
        items = list(category.items.order_by("sort_order", "name"))
        cache.set(cache_key, items, timeout=300)

    return render(
        request,
        "menu/category.html",
        {"category": category, "items": items},
    )

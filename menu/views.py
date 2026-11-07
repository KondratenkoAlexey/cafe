from django.core.cache import cache
from django.shortcuts import render

from .models import MENU_CACHE_KEY, Category


def public_menu(request):
    cached = cache.get(MENU_CACHE_KEY)
    if cached is not None:
        categories = cached
    else:
        categories = list(
            Category.objects.filter(is_active=True)
            .prefetch_related("items")
            .order_by("sort_order", "name")
        )
        # Materialize items for cache-friendly templates.
        payload = []
        for category in categories:
            items = list(category.items.all())
            payload.append({"category": category, "items": items})
        cache.set(MENU_CACHE_KEY, payload, timeout=300)
        categories = payload

    return render(request, "menu/public.html", {"categories": categories})

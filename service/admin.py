from django.contrib import admin

from .models import DiningTable, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ("number", "seats", "is_active")
    list_editable = ("seats", "is_active")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "waiter", "status", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menu_item", "quantity", "status")
    list_filter = ("status",)

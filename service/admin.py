from django.contrib import admin

from .models import DiningTable, Order, OrderItem, Receipt, ReceiptLine, Reservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0
    readonly_fields = ("name", "quantity", "unit_price", "line_total", "sort_order")
    can_delete = False


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


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "table_number", "total", "payment_method", "paid_at")
    list_filter = ("payment_method",)
    search_fields = ("number", "waiter_name")
    inlines = [ReceiptLineInline]
    readonly_fields = (
        "order",
        "number",
        "table_number",
        "waiter_name",
        "payment_method",
        "total",
        "vat_rate",
        "vat_amount",
        "paid_at",
    )


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("guest_name", "table", "starts_at", "party_size", "status", "phone")
    list_filter = ("status",)
    search_fields = ("guest_name", "phone")
    list_editable = ("status",)

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from menu import views as menu_views
from service import views as service_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", menu_views.public_menu, name="public_menu"),
    path("category/<int:category_id>/", menu_views.public_category, name="public_category"),
    path("staff/login/", service_views.staff_login, name="staff_login"),
    path("staff/logout/", service_views.staff_logout, name="staff_logout"),
    path("staff/", service_views.staff_home, name="staff_home"),
    path("staff/tables/", service_views.staff_tables, name="staff_tables"),
    path("staff/tables/<int:table_id>/", service_views.staff_table_detail, name="staff_table_detail"),
    path("staff/tables/<int:table_id>/open/", service_views.staff_open_order, name="staff_open_order"),
    path("staff/tables/<int:table_id>/add/", service_views.staff_add_item, name="staff_add_item"),
    path("staff/orders/<int:order_id>/send/", service_views.staff_send_kitchen, name="staff_send_kitchen"),
    path("staff/orders/<int:order_id>/served/", service_views.staff_mark_served, name="staff_mark_served"),
    path("staff/orders/<int:order_id>/paid/", service_views.staff_mark_paid, name="staff_mark_paid"),
    path("staff/orders/<int:order_id>/cancel/", service_views.staff_cancel_order, name="staff_cancel_order"),
    path("staff/items/<int:item_id>/cancel/", service_views.staff_cancel_item, name="staff_cancel_item"),
    path("staff/kitchen/", service_views.staff_kitchen, name="staff_kitchen"),
    path("staff/kitchen/<int:item_id>/cooking/", service_views.staff_item_cooking, name="staff_item_cooking"),
    path("staff/kitchen/<int:item_id>/ready/", service_views.staff_item_ready, name="staff_item_ready"),
    path("staff/menu/", service_views.staff_menu_manage, name="staff_menu_manage"),
    path("staff/menu/category/", service_views.staff_category_save, name="staff_category_save"),
    path("staff/menu/item/", service_views.staff_item_save, name="staff_item_save"),
    path("staff/menu/item/<int:item_id>/toggle/", service_views.staff_item_toggle, name="staff_item_toggle"),
    path("staff/menu/item/<int:item_id>/delete/", service_views.staff_item_delete, name="staff_item_delete"),
    path("staff/settings/", service_views.staff_settings, name="staff_settings"),
    path("staff/settings/table/", service_views.staff_table_save, name="staff_table_save"),
    path("staff/settings/table/<int:table_id>/delete/", service_views.staff_table_delete, name="staff_table_delete"),
    path("staff/settings/user/", service_views.staff_user_save, name="staff_user_save"),
    path("staff/settings/user/<int:user_id>/delete/", service_views.staff_user_delete, name="staff_user_delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

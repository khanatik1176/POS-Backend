from django.contrib import admin
from .models import (
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
    Product,
    PackageType,
    ReferenceNumber,
    Order,
    OrderItem,
)


@admin.register(PlatformType)
class PlatformTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")


@admin.register(PaymentMedium)
class PaymentMediumAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "color_code", "is_active", "sort_order")
    search_fields = ("name", "code")


@admin.register(CustomerStatus)
class CustomerStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")


class PackageTypeInline(admin.TabularInline):
    model = PackageType
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")
    inlines = [PackageTypeInline]


@admin.register(ReferenceNumber)
class ReferenceNumberAdmin(admin.ModelAdmin):
    list_display = ("id", "value", "created_at")
    search_fields = ("value",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "reference_number",
        "previous_reference",
        "status",
        "customer_status",
        "created_at",
    )
    search_fields = (
        "customer_name",
        "url",
        "reference_number__value",
        "previous_reference__value",
    )
    list_filter = ("status", "customer_status", "platform_type")
    inlines = [OrderItemInline]
from django.contrib import admin
from .models import (
    Product,
    PackageType,
    ReferenceNumber,
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
    Order,
    OrderItem,
)


class PackageTypeInline(admin.TabularInline):
    model = PackageType
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [PackageTypeInline]


@admin.register(ReferenceNumber)
class ReferenceNumberAdmin(admin.ModelAdmin):
    list_display = ('value', 'created_at')
    search_fields = ('value',)


@admin.register(PlatformType)
class PlatformTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(PaymentMedium)
class PaymentMediumAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(CustomerStatus)
class CustomerStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'reference_number', 'status', 'customer_status', 'entry_time')
    search_fields = ('customer_name', 'url', 'reference_number')
    list_filter = ('status', 'customer_status', 'platform_type')
    inlines = [OrderItemInline]

admin.site.register(PackageType)

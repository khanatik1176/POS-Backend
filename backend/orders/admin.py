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
    list_display = ('name', 'platform_type_names')
    search_fields = ('name',)
    inlines = [PackageTypeInline]
    filter_horizontal = ('platform_types',)

    def platform_type_names(self, obj):
        return ', '.join(obj.platform_types.values_list('name', flat=True)) or '-'

    platform_type_names.short_description = 'Platform types'


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
    list_display = ('customer_name', 'reference_number', 'status', 'customer_status', 'created_at')
    search_fields = ('customer_name', 'url', 'reference_number')
    list_filter = ('status', 'customer_status', 'platform_type')
    inlines = [OrderItemInline]

admin.site.register(PackageType)

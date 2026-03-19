from django.contrib import admin
from .models import Product, PackageType, ReferenceNumber, Order


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


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'product', 'package_type', 'status', 'customer_status', 'entry_time')
    search_fields = ('customer_name', 'url', 'reference_number__value')
    list_filter = ('status', 'customer_status', 'product')

admin.site.register(PackageType)

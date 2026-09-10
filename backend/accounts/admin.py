from django.contrib import admin

from .models import AuditLog, Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'ip_address', 'method', 'path', 'status_code')
    list_filter = ('method', 'status_code')
    search_fields = ('username', 'path', 'ip_address')
    date_hierarchy = 'created_at'

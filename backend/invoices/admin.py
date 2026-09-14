from django.contrib import admin

from .models import InvoiceImage, InvoiceRecord


class InvoiceImageInline(admin.TabularInline):
    model = InvoiceImage
    extra = 0
    fields = ('local_read_status', 'server_status', 'content_type', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(InvoiceRecord)
class InvoiceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'record_type', 'created_by', 'has_pending_server_review', 'notified', 'created_at')
    list_filter = ('record_type', 'has_pending_server_review', 'notified')
    search_fields = ('id',)
    inlines = [InvoiceImageInline]

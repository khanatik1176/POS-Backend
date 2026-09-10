from django.conf import settings
from django.db import models

from orders.models import TimeStampedModel


class InvoiceRecord(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_records',
    )
    fields = models.JSONField(default=dict)
    line_items = models.JSONField(default=list, blank=True)
    has_pending_server_review = models.BooleanField(default=False)
    notified = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        vendor = (self.fields or {}).get('vendor_name', {}).get('value') or 'Untitled'
        return f'Invoice #{self.id} - {vendor}'


class InvoiceImage(TimeStampedModel):
    LOCAL_STATUS_CHOICES = [
        ('ok', 'OK'),
        ('unreadable', 'Unreadable'),
    ]
    SERVER_STATUS_CHOICES = [
        ('not_needed', 'Not needed'),
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]

    record = models.ForeignKey(InvoiceRecord, on_delete=models.CASCADE, related_name='images')
    image_data = models.TextField()
    content_type = models.CharField(max_length=60, default='image/jpeg')
    local_read_status = models.CharField(max_length=20, choices=LOCAL_STATUS_CHOICES, default='ok')
    server_status = models.CharField(max_length=20, choices=SERVER_STATUS_CHOICES, default='not_needed')
    server_ocr_text = models.TextField(blank=True, default='')

    def __str__(self):
        return f'Image {self.id} for record {self.record_id}'

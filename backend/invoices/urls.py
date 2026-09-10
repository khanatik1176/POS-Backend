from django.urls import path

from .views import (
    InvoiceFieldTemplateAPIView,
    InvoiceImageDetailAPIView,
    InvoiceRecordDetailAPIView,
    InvoiceRecordListCreateAPIView,
    InvoiceRecordMarkSeenAPIView,
)

urlpatterns = [
    path('invoices/field-template/', InvoiceFieldTemplateAPIView.as_view(), name='invoice-field-template'),
    path('invoices/records/', InvoiceRecordListCreateAPIView.as_view(), name='invoice-records'),
    path('invoices/records/<int:pk>/', InvoiceRecordDetailAPIView.as_view(), name='invoice-record-detail'),
    path('invoices/records/<int:pk>/mark-seen/', InvoiceRecordMarkSeenAPIView.as_view(), name='invoice-record-mark-seen'),
    path('invoices/records/<int:pk>/images/<int:image_id>/', InvoiceImageDetailAPIView.as_view(), name='invoice-image-detail'),
]

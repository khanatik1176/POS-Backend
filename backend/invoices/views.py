import threading

from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import require_action

from .models import InvoiceImage, InvoiceRecord
from .ocr_service import process_record_escalation
from .record_types import FIELD_TEMPLATES
from .serializers import (
    InvoiceImageDetailSerializer,
    InvoiceRecordCreateSerializer,
    InvoiceRecordSerializer,
)


class InvoiceFieldTemplateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, require_action('ocr.view')]

    def get(self, request):
        return Response({'templates': FIELD_TEMPLATES})


class InvoiceRecordListCreateAPIView(generics.ListCreateAPIView):
    def get_permissions(self):
        action_key = 'ocr.create' if self.request.method == 'POST' else 'ocr.view'
        return [permissions.IsAuthenticated(), require_action(action_key)()]

    def get_queryset(self):
        return InvoiceRecord.objects.filter(created_by=self.request.user).prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InvoiceRecordCreateSerializer
        return InvoiceRecordSerializer

    @swagger_auto_schema(request_body=InvoiceRecordCreateSerializer, responses={201: InvoiceRecordSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        if record.has_pending_server_review:
            thread = threading.Thread(target=process_record_escalation, args=(record,), daemon=True)
            thread.start()

        return Response(InvoiceRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class InvoiceRecordDetailAPIView(generics.RetrieveAPIView):
    serializer_class = InvoiceRecordSerializer
    permission_classes = [permissions.IsAuthenticated, require_action('ocr.view')]

    def get_queryset(self):
        return InvoiceRecord.objects.filter(created_by=self.request.user).prefetch_related('images')


class InvoiceRecordMarkSeenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, require_action('ocr.view')]

    def post(self, request, pk):
        try:
            record = InvoiceRecord.objects.get(pk=pk, created_by=request.user)
        except InvoiceRecord.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        record.notified = True
        record.save(update_fields=['notified'])
        return Response(InvoiceRecordSerializer(record).data)


class InvoiceImageDetailAPIView(generics.RetrieveAPIView):
    serializer_class = InvoiceImageDetailSerializer
    permission_classes = [permissions.IsAuthenticated, require_action('ocr.view')]
    lookup_url_kwarg = 'image_id'

    def get_queryset(self):
        return InvoiceImage.objects.filter(record__created_by=self.request.user)

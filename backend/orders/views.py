from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_yasg.utils import swagger_auto_schema
import logging
from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.conf import settings

from .models import (
    Product,
    ReferenceNumber,
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
    Order,
)
from .serializers import (
    ProductSerializer,
    ReferenceNumberSerializer,
    PlatformTypeSerializer,
    PaymentMethodSerializer,
    PaymentMediumSerializer,
    OrderStatusSerializer,
    CustomerStatusSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    DeliverOrderSerializer,
)
from .telegram_bot import send_order_review_message, answer_callback, edit_review_message


logger = logging.getLogger(__name__)


def broadcast_order_event(event_type, order):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        'orders',
        {
            'type': 'order.event',
            'data': {
                'event': event_type,
                'order': OrderSerializer(order).data,
            },
        },
    )


class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Product.objects.prefetch_related('packages', 'platform_types').all().order_by('name')

        raw_platform = (
            self.request.query_params.get('platform_type')
            or self.request.query_params.get('platformType')
            or self.request.query_params.get('platform')
            or self.request.query_params.get('platform_code')
            or self.request.query_params.get('platformCode')
            or ''
        )
        platform_type = str(raw_platform).strip()
        if not platform_type:
            return queryset

        if platform_type.isdigit():
            return queryset.filter(platform_types__id=int(platform_type)).distinct()

        return queryset.filter(
            platform_types__code=platform_type.lower(),
        ).distinct()


class ReferenceSearchAPIView(generics.ListAPIView):
    serializer_class = ReferenceNumberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        search = self.request.query_params.get('search', '').strip()
        queryset = ReferenceNumber.objects.all().order_by('value')
        if search:
            queryset = queryset.filter(value__icontains=search)
        return queryset[:20]


class PlatformTypeListAPIView(generics.ListAPIView):
    queryset = PlatformType.objects.filter(is_active=True).prefetch_related('products__packages').order_by('name')
    serializer_class = PlatformTypeSerializer
    permission_classes = [AllowAny]


class PaymentMethodListAPIView(generics.ListAPIView):
    queryset = PaymentMethod.objects.filter(is_active=True).order_by('name')
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]


class PaymentMediumListAPIView(generics.ListAPIView):
    queryset = PaymentMedium.objects.filter(is_active=True).order_by('name')
    serializer_class = PaymentMediumSerializer
    permission_classes = [AllowAny]


class OrderStatusListAPIView(generics.ListAPIView):
    queryset = OrderStatus.objects.filter(is_active=True).order_by('name')
    serializer_class = OrderStatusSerializer
    permission_classes = [AllowAny]


class CustomerStatusListAPIView(generics.ListAPIView):
    queryset = CustomerStatus.objects.filter(is_active=True).order_by('name')
    serializer_class = CustomerStatusSerializer
    permission_classes = [AllowAny]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related(
        'platform_type', 'payment_method', 'payment_medium', 'status', 'customer_status', 'previous_reference'
    ).prefetch_related('items__product', 'items__package_type').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'customer_status', 'platform_type', 'payment_method', 'payment_medium']
    search_fields = ['customer_name', 'url', 'reference_number']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get('ordering')
        if ordering in ('entry_time', '-entry_time'):
            ordering = ordering.replace('entry_time', 'created_at')
            queryset = queryset.order_by(ordering)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @swagger_auto_schema(request_body=OrderCreateSerializer, responses={201: OrderSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        amount = serializer.validated_data.get('amount')
        send_order_review_message(order, amount=amount)
        broadcast_order_event('created', order)
        data = OrderSerializer(order).data
        return Response(data, status=status.HTTP_201_CREATED)

    def _resolve_status(self, code, fallback_name):
        status_obj = OrderStatus.objects.filter(code=code).first()
        if status_obj:
            return status_obj
        status_obj, _ = OrderStatus.objects.get_or_create(code=code, defaults={'name': fallback_name, 'is_active': True})
        return status_obj

    @swagger_auto_schema(methods=['post', 'patch'], request_body=None, responses={200: OrderSerializer})
    @action(detail=True, methods=['post', 'patch'])
    def verify(self, request, pk=None):
        order = self.get_object()
        if order.status and order.status.code == 'completed':
            return Response({'detail': 'Completed order cannot be verified again.'}, status=400)

        verified_status = self._resolve_status('verified', 'Verified')
        order.status = verified_status
        order.verified_at = timezone.now()
        order.save(update_fields=['status', 'verified_at', 'updated_at'])
        broadcast_order_event('verified', order)
        return Response(OrderSerializer(order).data)

    @swagger_auto_schema(methods=['post', 'patch'], request_body=DeliverOrderSerializer, responses={200: OrderSerializer})
    @action(detail=True, methods=['post', 'patch'])
    def deliver(self, request, pk=None):
        order = self.get_object()
        serializer = DeliverOrderSerializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        broadcast_order_event('delivered', order)
        return Response(OrderSerializer(order).data)


class TelegramWebhookAPIView(views.APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _resolve_status(self, code, fallback_name):
        status_obj = OrderStatus.objects.filter(code=code).first()
        if status_obj:
            return status_obj
        status_obj, _ = OrderStatus.objects.get_or_create(code=code, defaults={'name': fallback_name, 'is_active': True})
        return status_obj

    def post(self, request, *args, **kwargs):
        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if secret:
            incoming_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
            if incoming_secret != secret:
                logger.warning('Telegram webhook unauthorized: secret header mismatch')
                return Response({'detail': 'Unauthorized webhook'}, status=status.HTTP_401_UNAUTHORIZED)

        callback_query = request.data.get('callback_query')
        if not callback_query:
            return Response({'ok': True}, status=status.HTTP_200_OK)

        callback_id = callback_query.get('id')
        callback_data = callback_query.get('data', '')

        parts = callback_data.split('|')
        if len(parts) != 3 or parts[0] != 'ord':
            logger.warning('Telegram callback ignored due to invalid callback_data: %s', callback_data)
            answer_callback(callback_id, 'Invalid action')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        _, order_id, action = parts
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            logger.warning('Telegram callback order not found for id=%s', order_id)
            answer_callback(callback_id, 'Order not found')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        normalized_action = (action or '').strip().lower()

        if normalized_action in ('verify', 'verified'):
            status_obj = self._resolve_status('verified', 'Verified')
            order.status = status_obj
            order.verified_at = timezone.now()
            order.save(update_fields=['status', 'verified_at', 'updated_at'])
            answer_callback(callback_id, 'Order verified')
            result = 'Verified'
        elif normalized_action in ('decline', 'declined'):
            status_obj = self._resolve_status('declined', 'Declined')
            order.status = status_obj
            order.save(update_fields=['status', 'updated_at'])
            answer_callback(callback_id, 'Order declined')
            result = 'Declined'
        else:
            logger.warning('Telegram callback unknown action="%s" for order id=%s', action, order_id)
            answer_callback(callback_id, 'Unknown action')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        logger.info('Telegram callback processed: action=%s order_id=%s status=%s', normalized_action, order_id, status_obj.code)

        message = callback_query.get('message', {})
        chat_id = (message.get('chat') or {}).get('id')
        message_id = message.get('message_id')
        payment_medium = order.payment_medium.name if order.payment_medium else 'N/A'
        edit_review_message(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                'Order Review Completed\n\n'
                f'Reference No: {order.reference_number}\n'
                f'Payment Medium: {payment_medium}\n'
                f'Customer Name: {order.customer_name}\n'
                f'URL: {order.url}\n'
                f'Result: {result}'
            ),
        )

        broadcast_order_event(result.lower(), order)

        return Response({'ok': True}, status=status.HTTP_200_OK)

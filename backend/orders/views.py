from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

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
from .telegram_bot import send_order_for_review, answer_callback_query, edit_message


class ProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.prefetch_related('packages').all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


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
    queryset = PlatformType.objects.filter(is_active=True).order_by('name')
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        amount = request.data.get('amount')
        send_order_for_review(order, amount=amount)

        data = OrderSerializer(order).data
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        order = self.get_object()
        if order.status and order.status.code == 'completed':
            return Response({'detail': 'Completed order cannot be verified again.'}, status=400)

        verified_status = OrderStatus.objects.filter(code='verified').first()
        order.status = verified_status
        order.verified_at = timezone.now()
        order.save(update_fields=['status', 'verified_at', 'updated_at'])
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        order = self.get_object()
        serializer = DeliverOrderSerializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data)


class TelegramWebhookAPIView(views.APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        callback_query = request.data.get('callback_query')
        if not callback_query:
            return Response({'ok': True}, status=status.HTTP_200_OK)

        callback_id = callback_query.get('id')
        data = callback_query.get('data', '')
        if not data.startswith('ord|'):
            answer_callback_query(callback_id, 'Unknown action')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        parts = data.split('|')
        if len(parts) != 3:
            answer_callback_query(callback_id, 'Invalid action payload')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        _, order_id, action = parts
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            answer_callback_query(callback_id, 'Order not found')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        if action == 'ap':
            status_obj = OrderStatus.objects.filter(code='verified').first()
            order.status = status_obj
            order.verified_at = timezone.now()
            order.save(update_fields=['status', 'verified_at', 'updated_at'])
            answer_callback_query(callback_id, 'Order approved')
            result_text = 'Approved'
        elif action == 'dc':
            status_obj = OrderStatus.objects.filter(code='declined').first()
            if not status_obj:
                status_obj = OrderStatus.objects.filter(code='ordered').first()
            order.status = status_obj
            order.save(update_fields=['status', 'updated_at'])
            answer_callback_query(callback_id, 'Order declined')
            result_text = 'Declined'
        else:
            answer_callback_query(callback_id, 'Unknown action')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        message = callback_query.get('message', {})
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        message_id = message.get('message_id')
        if chat_id and message_id:
            payment_medium = order.payment_medium.name if order.payment_medium else 'N/A'
            edit_message(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    'Order Review Completed\n\n'
                    f'Order ID: {order.id}\n'
                    f'Reference No: {order.reference_number}\n'
                    f'Payment Medium: {payment_medium}\n'
                    f'Customer Name: {order.customer_name}\n'
                    f'URL: {order.url}\n'
                    f'Result: {result_text}'
                ),
            )

        return Response({'ok': True}, status=status.HTTP_200_OK)

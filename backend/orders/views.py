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

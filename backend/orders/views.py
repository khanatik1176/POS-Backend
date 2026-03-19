from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Product, ReferenceNumber, Order
from .serializers import (
    ProductSerializer,
    ReferenceNumberSerializer,
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


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related(
        'product', 'package_type', 'reference_number', 'previous_reference', 'delivered_reference', 'created_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'product', 'customer_status']
    search_fields = ['customer_name', 'url']
    ordering_fields = ['entry_time']
    ordering = ['-entry_time']

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
        if order.status == Order.Status.COMPLETED:
            return Response({'detail': 'Completed order cannot be verified again.'}, status=400)
        order.status = Order.Status.VERIFIED
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

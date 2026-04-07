from django.db.models import Q, Prefetch
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
    Product,
    PackageType,
    ReferenceNumber,
    Order,
    OrderItem,
)
from .serializers import (
    PlatformTypeSerializer,
    PaymentMethodSerializer,
    PaymentMediumSerializer,
    OrderStatusSerializer,
    CustomerStatusSerializer,
    ProductSerializer,
    ReferenceNumberSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    CompleteOrderSerializer,
)


class MasterDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "platform_types": PlatformTypeSerializer(
                PlatformType.objects.filter(is_active=True), many=True
            ).data,
            "payment_methods": PaymentMethodSerializer(
                PaymentMethod.objects.filter(is_active=True), many=True
            ).data,
            "payment_mediums": PaymentMediumSerializer(
                PaymentMedium.objects.filter(is_active=True), many=True
            ).data,
            "statuses": OrderStatusSerializer(
                OrderStatus.objects.filter(is_active=True), many=True
            ).data,
            "customer_statuses": CustomerStatusSerializer(
                CustomerStatus.objects.filter(is_active=True), many=True
            ).data,
            "products": ProductSerializer(
                Product.objects.filter(is_active=True).prefetch_related(
                    Prefetch(
                        "package_types",
                        queryset=PackageType.objects.filter(is_active=True)
                    )
                ),
                many=True
            ).data,
        }
        return Response(data)


class ReferenceSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()

        queryset = ReferenceNumber.objects.all()
        if q:
            queryset = queryset.filter(value__icontains=q)

        queryset = queryset.order_by("value")[:20]
        serializer = ReferenceNumberSerializer(queryset, many=True)
        return Response(serializer.data)


class OrderCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderListSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer

    def get_queryset(self):
        queryset = (
            Order.objects.select_related(
                "platform_type",
                "payment_method",
                "payment_medium",
                "status",
                "customer_status",
                "reference_number",
                "previous_reference",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product", "package_type")
                )
            )
            .all()
        )

        search = self.request.query_params.get("search", "").strip()
        status_code = self.request.query_params.get("status", "").strip()
        product_id = self.request.query_params.get("product_id", "").strip()
        customer_status = self.request.query_params.get("customer_status", "").strip()
        ordering = self.request.query_params.get("ordering", "-created_at").strip()

        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(url__icontains=search)
            )

        if status_code and status_code.lower() != "all":
            queryset = queryset.filter(
                Q(status__code__iexact=status_code) |
                Q(status__name__iexact=status_code)
            )

        if product_id:
            queryset = queryset.filter(items__product_id=product_id)

        if customer_status and customer_status.lower() != "all":
            queryset = queryset.filter(
                Q(customer_status__code__iexact=customer_status) |
                Q(customer_status__name__iexact=customer_status)
            )

        allowed_ordering = ["created_at", "-created_at"]
        if ordering not in allowed_ordering:
            ordering = "-created_at"

        return queryset.distinct().order_by(ordering)


class VerifyOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.select_related("status").get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=404)

        verified_status = OrderStatus.objects.filter(code="verified").first()
        if not verified_status:
            verified_status = OrderStatus.objects.filter(name__iexact="Verified").first()

        if not verified_status:
            return Response({"detail": "Verified status not found in database."}, status=400)

        order.status = verified_status
        order.verified_at = timezone.now()
        order.save(update_fields=["status", "verified_at", "updated_at"])

        return Response(OrderListSerializer(order).data)


class CompleteOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=404)

        serializer = CompleteOrderSerializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderListSerializer(order).data)
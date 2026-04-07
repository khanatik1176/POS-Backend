from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

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


class PlatformTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformType
        fields = ["id", "name", "code"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "code"]


class PaymentMediumSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMedium
        fields = ["id", "name", "code"]


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ["id", "name", "code", "color_code"]


class CustomerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerStatus
        fields = ["id", "name", "code"]


class PackageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageType
        fields = ["id", "name", "code", "product"]


class ProductSerializer(serializers.ModelSerializer):
    package_types = PackageTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "code", "package_types"]


class ReferenceNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceNumber
        fields = ["id", "value"]


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    package_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product_id = attrs["product_id"]
        package_type_id = attrs["package_type_id"]

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Invalid product."})

        try:
            package_type = PackageType.objects.get(
                id=package_type_id,
                product_id=product_id,
                is_active=True
            )
        except PackageType.DoesNotExist:
            raise serializers.ValidationError(
                {"package_type_id": "Invalid package type for selected product."}
            )

        attrs["product"] = product
        attrs["package_type"] = package_type
        return attrs


class OrderItemReadSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    package_type = PackageTypeSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "package_type", "quantity"]


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    url = serializers.URLField(max_length=500)
    platform_type_id = serializers.IntegerField()
    payment_method_id = serializers.IntegerField()
    payment_medium_id = serializers.IntegerField()
    status_id = serializers.IntegerField()
    customer_status_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    reference_number = serializers.CharField(max_length=100)

    previous_reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    items = OrderItemCreateSerializer(many=True)

    def validate(self, attrs):
        try:
            attrs["platform_type"] = PlatformType.objects.get(
                id=attrs["platform_type_id"], is_active=True
            )
        except PlatformType.DoesNotExist:
            raise serializers.ValidationError({"platform_type_id": "Invalid platform type."})

        try:
            attrs["payment_method"] = PaymentMethod.objects.get(
                id=attrs["payment_method_id"], is_active=True
            )
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError({"payment_method_id": "Invalid payment method."})

        try:
            attrs["payment_medium"] = PaymentMedium.objects.get(
                id=attrs["payment_medium_id"], is_active=True
            )
        except PaymentMedium.DoesNotExist:
            raise serializers.ValidationError({"payment_medium_id": "Invalid payment medium."})

        try:
            attrs["status"] = OrderStatus.objects.get(
                id=attrs["status_id"], is_active=True
            )
        except OrderStatus.DoesNotExist:
            raise serializers.ValidationError({"status_id": "Invalid status."})

        try:
            customer_status = CustomerStatus.objects.get(
                id=attrs["customer_status_id"], is_active=True
            )
        except CustomerStatus.DoesNotExist:
            raise serializers.ValidationError({"customer_status_id": "Invalid customer status."})

        attrs["customer_status"] = customer_status

        customer_status_code = (customer_status.code or customer_status.name).lower().strip()

        previous_reference = attrs.get("previous_reference")

        if customer_status_code == "renewal":
            if not previous_reference:
                raise serializers.ValidationError({
                    "previous_reference": "Previous reference is required for renewal customers."
                })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")

        reference_number_value = validated_data.pop("reference_number").strip()
        previous_reference_value = validated_data.pop("previous_reference", None)

        current_reference_obj, _ = ReferenceNumber.objects.get_or_create(
            value=reference_number_value
        )

        previous_reference_obj = None
        if previous_reference_value and previous_reference_value.strip():
            previous_reference_obj, _ = ReferenceNumber.objects.get_or_create(
                value=previous_reference_value.strip()
            )

        order = Order.objects.create(
            customer_name=validated_data["customer_name"],
            url=validated_data["url"],
            platform_type_master=validated_data["platform_type"],
            payment_method_master=validated_data["payment_method"],
            payment_medium_master=validated_data["payment_medium"],
            status_master=validated_data["status"],
            customer_status_master=validated_data["customer_status"],
            quantity=validated_data["quantity"],
            reference_number=current_reference_obj,
            previous_reference=previous_reference_obj,
        )

        order_items = []
        for item in items_data:
            order_items.append(
                OrderItem(
                    order=order,
                    product=item["product"],
                    package_type=item["package_type"],
                    quantity=item["quantity"],
                )
            )

        OrderItem.objects.bulk_create(order_items)
        return order


class OrderListSerializer(serializers.ModelSerializer):
    platform_type = PlatformTypeSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    payment_medium = PaymentMediumSerializer(read_only=True)
    status = OrderStatusSerializer(read_only=True)
    customer_status = CustomerStatusSerializer(read_only=True)
    reference_number = ReferenceNumberSerializer(read_only=True)
    previous_reference = ReferenceNumberSerializer(read_only=True)
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "url",
            "platform_type",
            "payment_method",
            "payment_medium",
            "status",
            "customer_status",
            "quantity",
            "reference_number",
            "previous_reference",
            "verified_at",
            "completed_at",
            "created_at",
            "items",
        ]


class CompleteOrderSerializer(serializers.Serializer):
    new_reference_number = serializers.CharField(max_length=100)

    @transaction.atomic
    def save(self, **kwargs):
        order = self.context["order"]

        new_reference_number = self.validated_data["new_reference_number"].strip()

        new_ref_obj, _ = ReferenceNumber.objects.get_or_create(value=new_reference_number)

        completed_status = OrderStatus.objects.filter(code="completed").first()
        if not completed_status:
            completed_status = OrderStatus.objects.filter(name__iexact="Completed").first()

        if not completed_status:
            raise serializers.ValidationError({"status": "Completed status not found in database."})

        order.reference_number = new_ref_obj
        order.status = completed_status
        order.completed_at = timezone.now()
        order.save(update_fields=["reference_number", "status", "completed_at", "updated_at"])
        return order
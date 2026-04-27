import uuid

from django.utils import timezone
from rest_framework import serializers
from .models import (
    Product,
    PackageType,
    ReferenceNumber,
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
    Order,
    OrderItem,
)


class ProductSerializer(serializers.ModelSerializer):
    packages = serializers.SerializerMethodField()
    platform_types = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'platform_types', 'packages']

    def get_packages(self, obj):
        return [{'id': package.id, 'name': package.name} for package in obj.packages.all().order_by('name')]

    def get_platform_types(self, obj):
        return [
            {'id': platform.id, 'code': platform.code, 'name': platform.name}
            for platform in obj.platform_types.all().order_by('name')
        ]


class ReferenceNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceNumber
        fields = ['id', 'value']


class LookupSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'code', 'name']


class PlatformTypeSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = PlatformType


class PaymentMethodSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = PaymentMethod


class PaymentMediumSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = PaymentMedium


class OrderStatusSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = OrderStatus


class CustomerStatusSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = CustomerStatus


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    package_type_name = serializers.CharField(source='package_type.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'package_type', 'package_type_name', 'quantity']

    def validate(self, attrs):
        product = attrs.get('product', getattr(self.instance, 'product', None))
        package_type = attrs.get('package_type', getattr(self.instance, 'package_type', None))
        if package_type and product and package_type.product_id != product.id:
            raise serializers.ValidationError({'package_type': 'Selected package does not belong to the selected product.'})
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    entry_time = serializers.DateTimeField(source='created_at', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    platform_type_detail = PlatformTypeSerializer(source='platform_type', read_only=True)
    payment_method_detail = PaymentMethodSerializer(source='payment_method', read_only=True)
    payment_medium_detail = PaymentMediumSerializer(source='payment_medium', read_only=True)
    status_detail = OrderStatusSerializer(source='status', read_only=True)
    customer_status_detail = CustomerStatusSerializer(source='customer_status', read_only=True)
    previous_reference_value = serializers.CharField(source='previous_reference.value', read_only=True)
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'url', 'platform_type', 'platform_type_detail', 'payment_method',
            'payment_method_detail', 'payment_medium', 'payment_medium_detail', 'reference_number',
            'status', 'status_detail', 'entry_time', 'customer_status', 'customer_status_detail',
            'previous_reference', 'previous_reference_value', 'delivered_reference', 'verified_at',
            'completed_at', 'created_by_username', 'items'
        ]
        read_only_fields = ['status', 'entry_time', 'verified_at', 'completed_at']

    def get_created_by_username(self, obj):
        return None

    def create(self, validated_data):
        return super().create(validated_data)


class OrderCreateItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    package_type = serializers.PrimaryKeyRelatedField(queryset=PackageType.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs['package_type'].product_id != attrs['product'].id:
            raise serializers.ValidationError({'package_type': 'Selected package does not belong to the selected product.'})
        return attrs


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    url = serializers.URLField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    platform_type = serializers.CharField()
    payment_method = serializers.CharField()
    payment_medium = serializers.CharField()
    reference_number = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    customer_status = serializers.CharField()
    previous_reference = serializers.CharField(max_length=120, allow_blank=True, required=False)
    items = OrderCreateItemSerializer(many=True, required=False)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)
    package_type = serializers.PrimaryKeyRelatedField(queryset=PackageType.objects.all(), required=False)
    quantity = serializers.IntegerField(min_value=1, required=False)

    def _resolve_lookup(self, model, value, field_name):
        value_str = str(value).strip()
        if not value_str:
            raise serializers.ValidationError({field_name: 'This field may not be blank.'})

        queryset = model.objects.filter(is_active=True)
        if value_str.isdigit():
            instance = queryset.filter(pk=int(value_str)).first()
            if instance:
                return instance

        instance = queryset.filter(code=value_str.lower()).first()
        if instance:
            return instance

        raise serializers.ValidationError({field_name: f'Invalid value: {value}'})

    def validate(self, attrs):
        attrs['platform_type'] = self._resolve_lookup(PlatformType, attrs.get('platform_type'), 'platform_type')
        attrs['payment_method'] = self._resolve_lookup(PaymentMethod, attrs.get('payment_method'), 'payment_method')
        attrs['payment_medium'] = self._resolve_lookup(PaymentMedium, attrs.get('payment_medium'), 'payment_medium')
        attrs['customer_status'] = self._resolve_lookup(CustomerStatus, attrs.get('customer_status'), 'customer_status')

        def validate_product_platform(product):
            allowed_platforms = product.platform_types.all()
            if allowed_platforms.exists() and not allowed_platforms.filter(pk=attrs['platform_type'].pk).exists():
                raise serializers.ValidationError({'product': 'Selected product is not available for the selected platform.'})

        items = attrs.get('items')
        if not items:
            product = attrs.get('product')
            package_type = attrs.get('package_type')
            quantity = attrs.get('quantity')

            if product and package_type and quantity:
                if package_type.product_id != product.id:
                    raise serializers.ValidationError({'package_type': 'Selected package does not belong to the selected product.'})

                validate_product_platform(product)

                attrs['items'] = [
                    {
                        'product': product,
                        'package_type': package_type,
                        'quantity': quantity,
                    }
                ]
            else:
                raise serializers.ValidationError({'items': 'At least one product item is required.'})
        else:
            for item in items:
                validate_product_platform(item['product'])

        if attrs['customer_status'].code == 'renewal' and not attrs.get('previous_reference'):
            raise serializers.ValidationError({'previous_reference': 'Previous reference is required for renewal customers.'})
        return attrs

    def _build_reference_number(self, data):
        reference_number = data.get('reference_number')
        if isinstance(reference_number, str):
            reference_number = reference_number.strip()

        if reference_number:
            return reference_number

        while True:
            generated = f'ORD-{timezone.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}'
            if not Order.objects.filter(reference_number=generated).exists() and not ReferenceNumber.objects.filter(value=generated).exists():
                return generated

    def create(self, validated_data):
        validated_data.pop('amount', None)
        items_data = validated_data.pop('items')
        validated_data.pop('product', None)
        validated_data.pop('package_type', None)
        validated_data.pop('quantity', None)
        ordered_status = OrderStatus.objects.filter(code='ordered').first()
        total_quantity = sum(item['quantity'] for item in items_data)

        reference_number = self._build_reference_number(validated_data)
        ReferenceNumber.objects.get_or_create(value=reference_number)
        validated_data.pop('reference_number', None)

        previous_reference_value = validated_data.pop('previous_reference', '').strip()
        previous_reference = None
        if previous_reference_value:
            previous_reference, _ = ReferenceNumber.objects.get_or_create(value=previous_reference_value)

        order = Order.objects.create(
            reference_number=reference_number,
            previous_reference=previous_reference,
            status=ordered_status,
            quantity=total_quantity,
            **validated_data,
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=item['product'],
                    package_type=item['package_type'],
                    quantity=item['quantity'],
                )
                for item in items_data
            ]
        )
        return order


class DeliverOrderSerializer(serializers.Serializer):
    delivered_reference = serializers.CharField(max_length=120, required=False, allow_blank=False)

    def validate(self, attrs):
        reference_value = attrs.get('delivered_reference')
        if reference_value in (None, ''):
            reference_value = self.initial_data.get('deliveredReference')

        if reference_value in (None, '') or not str(reference_value).strip():
            raise serializers.ValidationError({'delivered_reference': 'This field is required.'})

        attrs['delivered_reference'] = str(reference_value).strip()
        return attrs

    def save(self, **kwargs):
        order = self.context['order']
        reference_value = self.validated_data['delivered_reference']
        ReferenceNumber.objects.get_or_create(value=reference_value)
        completed_status, _ = OrderStatus.objects.get_or_create(
            code='completed',
            defaults={'name': 'Completed', 'is_active': True},
        )

        order.delivered_reference = reference_value
        order.status = completed_status
        order.completed_at = timezone.now()
        order.save(update_fields=['delivered_reference', 'status', 'completed_at', 'updated_at'])
        return order

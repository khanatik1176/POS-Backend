from django.utils import timezone
from rest_framework import serializers
from .models import Product, PackageType, ReferenceNumber, Order


class ProductSerializer(serializers.ModelSerializer):
    packages = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'packages']

    def get_packages(self, obj):
        return [{'id': package.id, 'name': package.name} for package in obj.packages.all().order_by('name')]


class ReferenceNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceNumber
        fields = ['id', 'value']


class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    package_type_name = serializers.CharField(source='package_type.name', read_only=True)
    reference_number_value = serializers.CharField(source='reference_number.value', read_only=True)
    previous_reference_value = serializers.CharField(source='previous_reference.value', read_only=True)
    delivered_reference_value = serializers.CharField(source='delivered_reference.value', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'url', 'platform_type', 'product', 'product_name', 'package_type',
            'package_type_name', 'quantity', 'payment_method', 'payment_medium', 'reference_number',
            'reference_number_value', 'status', 'entry_time', 'customer_status', 'previous_reference',
            'previous_reference_value', 'delivered_reference', 'delivered_reference_value', 'verified_at',
            'completed_at', 'created_by_username'
        ]
        read_only_fields = ['status', 'entry_time', 'verified_at', 'completed_at']

    def validate(self, attrs):
        customer_status = attrs.get('customer_status', getattr(self.instance, 'customer_status', None))
        previous_reference = attrs.get('previous_reference', getattr(self.instance, 'previous_reference', None))
        product = attrs.get('product', getattr(self.instance, 'product', None))
        package_type = attrs.get('package_type', getattr(self.instance, 'package_type', None))

        if customer_status == Order.CustomerStatus.RENEWAL and not previous_reference:
            raise serializers.ValidationError({'previous_reference': 'Previous reference is required for renewal customers.'})

        if package_type and product and package_type.product_id != product.id:
            raise serializers.ValidationError({'package_type': 'Selected package does not belong to the selected product.'})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    url = serializers.URLField()
    platform_type = serializers.ChoiceField(choices=Order.PlatformType.choices)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    package_type = serializers.PrimaryKeyRelatedField(queryset=PackageType.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    payment_medium = serializers.ChoiceField(choices=Order.PaymentMedium.choices)
    reference_number = serializers.CharField(max_length=120)
    customer_status = serializers.ChoiceField(choices=Order.CustomerStatus.choices)
    previous_reference = serializers.CharField(max_length=120, allow_blank=True, required=False)

    def validate(self, attrs):
        if attrs['package_type'].product_id != attrs['product'].id:
            raise serializers.ValidationError({'package_type': 'Selected package does not belong to the selected product.'})

        if attrs['customer_status'] == Order.CustomerStatus.RENEWAL and not attrs.get('previous_reference'):
            raise serializers.ValidationError({'previous_reference': 'Previous reference is required for renewal customers.'})
        return attrs

    def create(self, validated_data):
        reference, _ = ReferenceNumber.objects.get_or_create(value=validated_data.pop('reference_number').strip())

        previous_reference_value = validated_data.pop('previous_reference', '').strip()
        previous_reference = None
        if previous_reference_value:
            previous_reference, _ = ReferenceNumber.objects.get_or_create(value=previous_reference_value)

        request = self.context.get('request')
        return Order.objects.create(
            reference_number=reference,
            previous_reference=previous_reference,
            created_by=request.user if request and request.user.is_authenticated else None,
            **validated_data,
        )


class DeliverOrderSerializer(serializers.Serializer):
    delivered_reference = serializers.CharField(max_length=120)

    def save(self, **kwargs):
        order = self.context['order']
        reference_value = self.validated_data['delivered_reference'].strip()
        reference, _ = ReferenceNumber.objects.get_or_create(value=reference_value)
        order.delivered_reference = reference
        order.status = Order.Status.COMPLETED
        order.completed_at = timezone.now()
        order.save(update_fields=['delivered_reference', 'status', 'completed_at', 'updated_at'])
        return order

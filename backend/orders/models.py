from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LookupBaseModel(models.Model):
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120, unique=True)
    platform_types = models.ManyToManyField(
        'PlatformType',
        related_name='products',
        blank=True,
    )

    def __str__(self):
        return self.name


class PackageType(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packages')
    name = models.CharField(max_length=120)

    class Meta:
        unique_together = ('product', 'name')

    def __str__(self):
        return f'{self.product.name} - {self.name}'


class ReferenceNumber(TimeStampedModel):
    value = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.value


class PlatformType(LookupBaseModel):
    pass


class PaymentMethod(LookupBaseModel):
    pass


class PaymentMedium(LookupBaseModel):
    pass


class OrderStatus(LookupBaseModel):
    pass


class CustomerStatus(LookupBaseModel):
    pass


class Order(TimeStampedModel):
    customer_name = models.CharField(max_length=255)
    url = models.URLField()
    quantity = models.PositiveIntegerField(default=1)
    platform_type = models.ForeignKey(
        PlatformType,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='platform_type_master_id',
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='payment_method_master_id',
    )
    payment_medium = models.ForeignKey(
        PaymentMedium,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='payment_medium_master_id',
    )
    reference_number = models.CharField(max_length=120, db_column='old_reference_number')
    previous_reference = models.ForeignKey(
        ReferenceNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='renewal_orders',
    )
    delivered_reference = models.CharField(max_length=120, null=True, blank=True, db_column='old_previous_reference')
    status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='status_master_id',
    )
    customer_status = models.ForeignKey(
        CustomerStatus,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
        db_column='customer_status_master_id',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer_name} - {self.reference_number}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    package_type = models.ForeignKey(PackageType, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Order #{self.order_id} - {self.product.name} / {self.package_type.name}'

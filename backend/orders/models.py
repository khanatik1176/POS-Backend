from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class MasterBase(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=120, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class PlatformType(MasterBase):
    pass


class PaymentMethod(MasterBase):
    pass


class PaymentMedium(MasterBase):
    pass


class OrderStatus(MasterBase):
    color_code = models.CharField(max_length=20, blank=True, null=True)


class CustomerStatus(MasterBase):
    pass


class Product(MasterBase):
    pass


class PackageType(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="package_types")
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=120, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "name")

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ReferenceNumber(TimeStampedModel):
    value = models.CharField(max_length=100, unique=True, db_index=True)

    def __str__(self):
        return self.value


class Order(TimeStampedModel):
    customer_name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)

    # OLD EXISTING TEXT FIELDS - keep them for now
    platform_type = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    payment_medium = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    customer_status = models.CharField(max_length=100, null=True, blank=True)
    product_name = models.CharField(max_length=255, null=True, blank=True)
    package_type = models.CharField(max_length=255, null=True, blank=True)
    old_reference_number = models.CharField(max_length=100, null=True, blank=True)
    old_previous_reference = models.CharField(max_length=100, null=True, blank=True)

    quantity = models.PositiveIntegerField(default=1)

    # NEW FK FIELDS - use new names for now
    platform_type_master = models.ForeignKey(
        PlatformType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders"
    )
    payment_method_master = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders"
    )
    payment_medium_master = models.ForeignKey(
        PaymentMedium,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders"
    )
    status_master = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders"
    )
    customer_status_master = models.ForeignKey(
        CustomerStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders"
    )
    reference_number = models.ForeignKey(
        ReferenceNumber,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_orders"
    )
    previous_reference = models.ForeignKey(
        ReferenceNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewal_orders"
    )
    
    verified_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.customer_name


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    package_type = models.ForeignKey(PackageType, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
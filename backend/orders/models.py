from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Product(models.Model):
    name = models.CharField(max_length=120, unique=True)

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


class Order(TimeStampedModel):
    class PlatformType(models.TextChoices):
        FACEBOOK = 'facebook', 'Facebook'
        INSTAGRAM = 'instagram', 'Instagram'
        YOUTUBE = 'youtube', 'YouTube'
        WEBSITE = 'website', 'Website'
        TIKTOK = 'tiktok', 'TikTok'
        OTHER = 'other', 'Other'

    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        BANK = 'bank', 'Bank Transfer'
        CARD = 'card', 'Card'
        CASH = 'cash', 'Cash'

    class PaymentMedium(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        MOBILE_BANKING = 'mobile_banking', 'Mobile Banking'
        POS = 'pos', 'POS'

    class Status(models.TextChoices):
        ORDERED = 'ordered', 'Ordered'
        VERIFIED = 'verified', 'Verified'
        COMPLETED = 'completed', 'Completed'

    class CustomerStatus(models.TextChoices):
        NEW = 'new', 'New'
        RENEWAL = 'renewal', 'Renewal'

    customer_name = models.CharField(max_length=255)
    url = models.URLField()
    platform_type = models.CharField(max_length=30, choices=PlatformType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    package_type = models.ForeignKey(PackageType, on_delete=models.PROTECT, related_name='orders')
    quantity = models.PositiveIntegerField(default=1)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)
    payment_medium = models.CharField(max_length=30, choices=PaymentMedium.choices)
    reference_number = models.ForeignKey(ReferenceNumber, on_delete=models.PROTECT, related_name='primary_orders')
    previous_reference = models.ForeignKey(
        ReferenceNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='renewal_orders',
    )
    delivered_reference = models.ForeignKey(
        ReferenceNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivered_orders',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED)
    entry_time = models.DateTimeField(auto_now_add=True)
    customer_status = models.CharField(max_length=20, choices=CustomerStatus.choices)
    verified_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-entry_time']

    def __str__(self):
        return f'{self.customer_name} - {self.product.name}'

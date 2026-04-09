from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import (
    Product,
    PackageType,
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
)


SEED_PRODUCTS = {
    'Facebook Boost': ['Basic', 'Standard', 'Premium'],
    'YouTube Watch Time': ['1000 Hours', '4000 Hours'],
    'Instagram Growth': ['Starter', 'Business', 'Creator'],
}

PLATFORM_TYPES = [
    ('facebook', 'Facebook'),
    ('instagram', 'Instagram'),
    ('youtube', 'YouTube'),
    ('website', 'Website'),
    ('tiktok', 'TikTok'),
    ('other', 'Other'),
]

PAYMENT_METHODS = [
    ('bkash', 'bKash'),
    ('nagad', 'Nagad'),
    ('bank', 'Bank Transfer'),
    ('card', 'Card'),
    ('cash', 'Cash'),
]

PAYMENT_MEDIA = [
    ('online', 'Online'),
    ('offline', 'Offline'),
    ('mobile_banking', 'Mobile Banking'),
    ('pos', 'POS'),
]

ORDER_STATUSES = [
    ('ordered', 'Ordered'),
    ('verified', 'Verified'),
    ('completed', 'Completed'),
    ('declined', 'Declined'),
]

CUSTOMER_STATUSES = [
    ('new', 'New'),
    ('renewal', 'Renewal'),
]


class Command(BaseCommand):
    help = 'Seed initial products, packages, and an admin user.'

    def handle(self, *args, **options):
        for product_name, packages in SEED_PRODUCTS.items():
            product, _ = Product.objects.get_or_create(name=product_name)
            for package_name in packages:
                PackageType.objects.get_or_create(product=product, name=package_name)

        for code, name in PLATFORM_TYPES:
            PlatformType.objects.get_or_create(code=code, defaults={'name': name})

        for code, name in PAYMENT_METHODS:
            PaymentMethod.objects.get_or_create(code=code, defaults={'name': name})

        for code, name in PAYMENT_MEDIA:
            PaymentMedium.objects.get_or_create(code=code, defaults={'name': name})

        for code, name in ORDER_STATUSES:
            OrderStatus.objects.get_or_create(code=code, defaults={'name': name})

        for code, name in CUSTOMER_STATUSES:
            CustomerStatus.objects.get_or_create(code=code, defaults={'name': name})

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin1234')
            self.stdout.write(self.style.SUCCESS('Created default admin user: admin / admin1234'))

        self.stdout.write(self.style.SUCCESS('Seed complete.'))

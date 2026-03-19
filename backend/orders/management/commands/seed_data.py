from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import Product, PackageType


SEED_PRODUCTS = {
    'Facebook Boost': ['Basic', 'Standard', 'Premium'],
    'YouTube Watch Time': ['1000 Hours', '4000 Hours'],
    'Instagram Growth': ['Starter', 'Business', 'Creator'],
}


class Command(BaseCommand):
    help = 'Seed initial products, packages, and an admin user.'

    def handle(self, *args, **options):
        for product_name, packages in SEED_PRODUCTS.items():
            product, _ = Product.objects.get_or_create(name=product_name)
            for package_name in packages:
                PackageType.objects.get_or_create(product=product, name=package_name)

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin1234')
            self.stdout.write(self.style.SUCCESS('Created default admin user: admin / admin1234'))

        self.stdout.write(self.style.SUCCESS('Seed complete.'))

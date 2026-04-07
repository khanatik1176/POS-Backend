from django.core.management.base import BaseCommand

from orders.models import (
    PlatformType,
    PaymentMethod,
    PaymentMedium,
    OrderStatus,
    CustomerStatus,
)


class Command(BaseCommand):
    help = "Seed master data"

    def handle(self, *args, **kwargs):
        platform_types = [
            ("Facebook", "facebook"),
            ("Instagram", "instagram"),
            ("YouTube", "youtube"),
            ("Website", "website"),
            ("TikTok", "tiktok"),
            ("Other", "other"),
        ]

        payment_methods = [
            ("bKash", "bkash"),
            ("Nagad", "nagad"),
            ("Bank Transfer", "bank"),
            ("Card", "card"),
            ("Cash", "cash"),
        ]

        payment_mediums = [
            ("Online", "online"),
            ("Offline", "offline"),
            ("Mobile Banking", "mobile_banking"),
            ("POS", "pos"),
        ]

        statuses = [
            ("Ordered", "ordered", "blue"),
            ("Verified", "verified", "green"),
            ("Completed", "completed", "gray"),
        ]

        customer_statuses = [
            ("New", "new"),
            ("Renewal", "renewal"),
        ]

        for i, (name, code) in enumerate(platform_types, start=1):
            PlatformType.objects.get_or_create(
                code=code,
                defaults={"name": name, "sort_order": i}
            )

        for i, (name, code) in enumerate(payment_methods, start=1):
            PaymentMethod.objects.get_or_create(
                code=code,
                defaults={"name": name, "sort_order": i}
            )

        for i, (name, code) in enumerate(payment_mediums, start=1):
            PaymentMedium.objects.get_or_create(
                code=code,
                defaults={"name": name, "sort_order": i}
            )

        for i, (name, code, color_code) in enumerate(statuses, start=1):
            OrderStatus.objects.get_or_create(
                code=code,
                defaults={"name": name, "color_code": color_code, "sort_order": i}
            )

        for i, (name, code) in enumerate(customer_statuses, start=1):
            CustomerStatus.objects.get_or_create(
                code=code,
                defaults={"name": name, "sort_order": i}
            )

        self.stdout.write(self.style.SUCCESS("Master data seeded successfully."))
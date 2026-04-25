from django.db import migrations, models


def forwards_populate_product_platform_types(apps, schema_editor):
    Product = apps.get_model('orders', 'Product')
    PlatformType = apps.get_model('orders', 'PlatformType')

    platform_type_map = {
        'Facebook Boost': ['facebook'],
        'YouTube Watch Time': ['youtube'],
        'Instagram Growth': ['instagram'],
    }

    for product_name, platform_codes in platform_type_map.items():
        product = Product.objects.filter(name=product_name).first()
        if not product:
            continue

        platform_types = PlatformType.objects.filter(code__in=platform_codes)
        product.platform_types.set(platform_types)


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_schema_guard_add_expected_order_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='platform_types',
            field=models.ManyToManyField(blank=True, related_name='products', to='orders.platformtype'),
        ),
        migrations.RunPython(forwards_populate_product_platform_types, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'orders_order'
                      AND column_name = 'reference_number'
                ) THEN
                    EXECUTE 'ALTER TABLE orders_order ALTER COLUMN reference_number DROP NOT NULL';
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
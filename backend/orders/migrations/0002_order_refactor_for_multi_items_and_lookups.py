from django.db import migrations, models
import django.db.models.deletion


def forwards_populate_new_order_fields(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    OrderItem = apps.get_model('orders', 'OrderItem')
    PlatformType = apps.get_model('orders', 'PlatformType')
    PaymentMethod = apps.get_model('orders', 'PaymentMethod')
    PaymentMedium = apps.get_model('orders', 'PaymentMedium')
    OrderStatus = apps.get_model('orders', 'OrderStatus')
    CustomerStatus = apps.get_model('orders', 'CustomerStatus')

    for order in Order.objects.select_related('reference_number', 'delivered_reference').all():
        if getattr(order, 'reference_number_id', None):
            order.reference_number_text = order.reference_number.value

        if getattr(order, 'delivered_reference_id', None):
            order.delivered_reference_text = order.delivered_reference.value

        if getattr(order, 'platform_type', None):
            platform, _ = PlatformType.objects.get_or_create(
                code=order.platform_type,
                defaults={'name': order.platform_type.replace('_', ' ').title()},
            )
            order.platform_type_lookup = platform

        if getattr(order, 'payment_method', None):
            payment_method, _ = PaymentMethod.objects.get_or_create(
                code=order.payment_method,
                defaults={'name': order.payment_method.replace('_', ' ').title()},
            )
            order.payment_method_lookup = payment_method

        if getattr(order, 'payment_medium', None):
            payment_medium, _ = PaymentMedium.objects.get_or_create(
                code=order.payment_medium,
                defaults={'name': order.payment_medium.replace('_', ' ').title()},
            )
            order.payment_medium_lookup = payment_medium

        if getattr(order, 'status', None):
            status, _ = OrderStatus.objects.get_or_create(
                code=order.status,
                defaults={'name': order.status.replace('_', ' ').title()},
            )
            order.status_lookup = status

        if getattr(order, 'customer_status', None):
            customer_status, _ = CustomerStatus.objects.get_or_create(
                code=order.customer_status,
                defaults={'name': order.customer_status.replace('_', ' ').title()},
            )
            order.customer_status_lookup = customer_status

        OrderItem.objects.create(
            order_id=order.id,
            product_id=order.product_id,
            package_type_id=order.package_type_id,
            quantity=order.quantity,
        )

        order.save(update_fields=[
            'reference_number_text',
            'delivered_reference_text',
            'platform_type_lookup',
            'payment_method_lookup',
            'payment_medium_lookup',
            'status_lookup',
            'customer_status_lookup',
        ])


def backwards_noop(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='OrderStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PaymentMedium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PlatformType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('package_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='orders.packagetype')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='orders.product')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='customer_status_lookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.customerstatus'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivered_reference_text',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_medium_lookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.paymentmedium'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method_lookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.paymentmethod'),
        ),
        migrations.AddField(
            model_name='order',
            name='platform_type_lookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.platformtype'),
        ),
        migrations.AddField(
            model_name='order',
            name='reference_number_text',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='status_lookup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.orderstatus'),
        ),
        migrations.RunPython(forwards_populate_new_order_fields, backwards_noop),
        migrations.RemoveField(
            model_name='order',
            name='customer_status',
        ),
        migrations.RemoveField(
            model_name='order',
            name='delivered_reference',
        ),
        migrations.RemoveField(
            model_name='order',
            name='package_type',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_medium',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_method',
        ),
        migrations.RemoveField(
            model_name='order',
            name='platform_type',
        ),
        migrations.RemoveField(
            model_name='order',
            name='product',
        ),
        migrations.RemoveField(
            model_name='order',
            name='quantity',
        ),
        migrations.RemoveField(
            model_name='order',
            name='reference_number',
        ),
        migrations.RemoveField(
            model_name='order',
            name='status',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='customer_status_lookup',
            new_name='customer_status',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='delivered_reference_text',
            new_name='delivered_reference',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='payment_medium_lookup',
            new_name='payment_medium',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='payment_method_lookup',
            new_name='payment_method',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='platform_type_lookup',
            new_name='platform_type',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='reference_number_text',
            new_name='reference_number',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='status_lookup',
            new_name='status',
        ),
        migrations.AlterField(
            model_name='order',
            name='reference_number',
            field=models.CharField(max_length=120),
        ),
    ]

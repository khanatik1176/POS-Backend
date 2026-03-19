from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='ReferenceNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('value', models.CharField(max_length=120, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PackageType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='orders.product')),
            ],
            options={'unique_together': {('product', 'name')}},
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer_name', models.CharField(max_length=255)),
                ('url', models.URLField()),
                ('platform_type', models.CharField(choices=[('facebook', 'Facebook'), ('instagram', 'Instagram'), ('youtube', 'YouTube'), ('website', 'Website'), ('tiktok', 'TikTok'), ('other', 'Other')], max_length=30)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('payment_method', models.CharField(choices=[('bkash', 'bKash'), ('nagad', 'Nagad'), ('bank', 'Bank Transfer'), ('card', 'Card'), ('cash', 'Cash')], max_length=30)),
                ('payment_medium', models.CharField(choices=[('online', 'Online'), ('offline', 'Offline'), ('mobile_banking', 'Mobile Banking'), ('pos', 'POS')], max_length=30)),
                ('status', models.CharField(choices=[('ordered', 'Ordered'), ('verified', 'Verified'), ('completed', 'Completed')], default='ordered', max_length=20)),
                ('entry_time', models.DateTimeField(auto_now_add=True)),
                ('customer_status', models.CharField(choices=[('new', 'New'), ('renewal', 'Renewal')], max_length=20)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('delivered_reference', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delivered_orders', to='orders.referencenumber')),
                ('package_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.packagetype')),
                ('previous_reference', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='renewal_orders', to='orders.referencenumber')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='orders.product')),
                ('reference_number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='primary_orders', to='orders.referencenumber')),
            ],
            options={'ordering': ['-entry_time']},
        ),
    ]

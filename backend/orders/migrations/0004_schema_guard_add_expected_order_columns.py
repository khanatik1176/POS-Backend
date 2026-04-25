from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_order_options_remove_order_created_by_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS quantity integer NOT NULL DEFAULT 1;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS platform_type_master_id bigint NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS payment_method_master_id bigint NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS payment_medium_master_id bigint NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS status_master_id bigint NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS customer_status_master_id bigint NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS old_reference_number varchar(120) NULL;
            ALTER TABLE orders_order ADD COLUMN IF NOT EXISTS old_previous_reference varchar(120) NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

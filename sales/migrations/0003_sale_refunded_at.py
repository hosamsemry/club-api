from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0002_saleitem_cost_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="refunded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(fields=["club", "refunded_at"], name="sales_sale_club_id_refunded_idx"),
        ),
    ]

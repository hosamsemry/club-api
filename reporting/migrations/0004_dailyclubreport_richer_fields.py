from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0003_rename_reporting_d_club_id_d77857_idx_reporting_d_club_id_98c1e5_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyclubreport",
            name="activity_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="dailyclubreport",
            name="revenue_breakdown",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="dailyclubreport",
            name="top_products",
            field=models.JSONField(blank=True, default=list),
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("clubs", "0003_club_timezone"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyClubReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("report_date", models.DateField()),
                ("timezone", models.CharField(max_length=64)),
                ("source_window_start", models.DateTimeField()),
                ("source_window_end", models.DateTimeField()),
                ("sales_count", models.PositiveIntegerField(default=0)),
                ("total_revenue", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("audit_action_counts", models.JSONField(blank=True, default=dict)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_reports",
                        to="clubs.club",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["club", "report_date"], name="reporting_d_club_id_d77857_idx"),
                    models.Index(fields=["report_date"], name="reporting_d_report__0f9786_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("club", "report_date"), name="unique_daily_report_per_club_date"
                    )
                ],
            },
        ),
    ]

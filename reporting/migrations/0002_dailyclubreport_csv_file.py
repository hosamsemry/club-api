from django.db import migrations, models
import reporting.models


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyclubreport",
            name="csv_file",
            field=models.FileField(blank=True, null=True, upload_to=reporting.models.daily_report_csv_upload_to),
        ),
    ]

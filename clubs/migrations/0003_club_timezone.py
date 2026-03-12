from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0002_club_clubs_club_slug_9373ca_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="club",
            name="timezone",
            field=models.CharField(default="UTC", max_length=64),
        ),
    ]

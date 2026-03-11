from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0002_club_clubs_club_slug_9373ca_idx_and_more"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="club",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="users",
                to="clubs.club",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("owner", "Owner"),
                    ("manager", "Manager"),
                    ("cashier", "Cashier"),
                    ("staff", "Staff"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]

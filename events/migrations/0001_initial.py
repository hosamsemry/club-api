import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("clubs", "0003_club_timezone"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OccasionType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events_occasiontypes",
                        to="clubs.club",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="VenueReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("guest_name", models.CharField(max_length=255)),
                ("guest_phone", models.CharField(max_length=30)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("guest_count", models.PositiveIntegerField()),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("refunded_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "payment_status",
                    models.CharField(
                        choices=[("unpaid", "Unpaid"), ("partial", "Partial"), ("paid", "Paid"), ("refunded", "Refunded")],
                        default="unpaid",
                        max_length=20,
                    ),
                ),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("refunded_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events_venuereservations",
                        to="clubs.club",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="venue_reservations_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "occasion_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="events.occasiontype",
                    ),
                ),
            ],
            options={
                "ordering": ["-starts_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="occasiontype",
            constraint=models.UniqueConstraint(
                fields=("club", "name"),
                name="unique_occasion_type_name_per_club",
            ),
        ),
        migrations.AddIndex(
            model_name="occasiontype",
            index=models.Index(fields=["club", "is_active"], name="events_occa_club_id_5fd6d0_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "starts_at"], name="events_venu_club_id_2b50b1_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "ends_at"], name="events_venu_club_id_4a8d01_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "status"], name="events_venu_club_id_6df9d5_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "payment_status"], name="events_venu_club_id_d8752d_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "occasion_type"], name="events_venu_club_id_446974_idx"),
        ),
        migrations.AddIndex(
            model_name="venuereservation",
            index=models.Index(fields=["club", "guest_phone"], name="events_venu_club_id_a58fa5_idx"),
        ),
    ]

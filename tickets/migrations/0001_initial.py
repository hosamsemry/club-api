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
            name="GateEntryDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("visit_date", models.DateField()),
                ("daily_capacity", models.PositiveIntegerField()),
                ("is_open", models.BooleanField(default=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets_gateentrydays",
                        to="clubs.club",
                    ),
                ),
            ],
            options={"ordering": ["-visit_date"]},
        ),
        migrations.CreateModel(
            name="GateTicketSale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("buyer_name", models.CharField(max_length=255)),
                ("buyer_phone", models.CharField(max_length=30)),
                ("visit_date", models.DateField()),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("issued", "Issued"), ("voided", "Voided")], default="issued", max_length=20)),
                ("notes", models.TextField(blank=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets_gateticketsales",
                        to="clubs.club",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gate_ticket_sales_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GateTicketType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=100)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("display_order", models.PositiveIntegerField(default=0)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets_gatetickettypes",
                        to="clubs.club",
                    ),
                ),
            ],
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.CreateModel(
            name="GateTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("visit_date", models.DateField()),
                ("code", models.CharField(max_length=32, unique=True)),
                ("status", models.CharField(choices=[("issued", "Issued"), ("checked_in", "Checked In"), ("voided", "Voided")], default="issued", max_length=20)),
                ("checked_in_at", models.DateTimeField(blank=True, null=True)),
                (
                    "checked_in_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gate_tickets_checked_in",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets_gatetickets",
                        to="clubs.club",
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="tickets.gateticketsale",
                    ),
                ),
                (
                    "ticket_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tickets",
                        to="tickets.gatetickettype",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="gateentryday",
            constraint=models.UniqueConstraint(fields=("club", "visit_date"), name="unique_gate_entry_day_per_club_date"),
        ),
        migrations.AddConstraint(
            model_name="gatetickettype",
            constraint=models.UniqueConstraint(fields=("club", "name"), name="unique_gate_ticket_type_name_per_club"),
        ),
        migrations.AddIndex(
            model_name="gateentryday",
            index=models.Index(fields=["club", "visit_date"], name="tickets_gat_club_id_887665_idx"),
        ),
        migrations.AddIndex(
            model_name="gateentryday",
            index=models.Index(fields=["club", "is_open"], name="tickets_gat_club_id_0defd1_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticketsale",
            index=models.Index(fields=["club", "visit_date"], name="tickets_gat_club_id_59c5de_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticketsale",
            index=models.Index(fields=["club", "status"], name="tickets_gat_club_id_0f727a_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticketsale",
            index=models.Index(fields=["club", "buyer_phone"], name="tickets_gat_club_id_3442eb_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticketsale",
            index=models.Index(fields=["club", "created_by"], name="tickets_gat_club_id_4216a5_idx"),
        ),
        migrations.AddIndex(
            model_name="gatetickettype",
            index=models.Index(fields=["club", "is_active"], name="tickets_gat_club_id_52e638_idx"),
        ),
        migrations.AddIndex(
            model_name="gatetickettype",
            index=models.Index(fields=["club", "display_order"], name="tickets_gat_club_id_716dcc_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticket",
            index=models.Index(fields=["club", "visit_date"], name="tickets_gat_club_id_744733_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticket",
            index=models.Index(fields=["club", "status"], name="tickets_gat_club_id_560f8d_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticket",
            index=models.Index(fields=["club", "ticket_type"], name="tickets_gat_club_id_c237e5_idx"),
        ),
        migrations.AddIndex(
            model_name="gateticket",
            index=models.Index(fields=["code"], name="tickets_gat_code_03cb0b_idx"),
        ),
    ]

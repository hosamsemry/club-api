from django.conf import settings
from django.db import models

from clubs.models import TenantBaseModel


class GateTicketType(TenantBaseModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club", "name"],
                name="unique_gate_ticket_type_name_per_club",
            )
        ]
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["club", "display_order"]),
        ]
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class GateEntryDay(TenantBaseModel):
    visit_date = models.DateField()
    daily_capacity = models.PositiveIntegerField()
    is_open = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club", "visit_date"],
                name="unique_gate_entry_day_per_club_date",
            )
        ]
        indexes = [
            models.Index(fields=["club", "visit_date"]),
            models.Index(fields=["club", "is_open"]),
        ]
        ordering = ["-visit_date"]

    def __str__(self):
        return f"{self.club.name} - {self.visit_date}"


class GateTicketSale(TenantBaseModel):
    STATUS_ISSUED = "issued"
    STATUS_VOIDED = "voided"
    STATUS_CHOICES = [
        (STATUS_ISSUED, "Issued"),
        (STATUS_VOIDED, "Voided"),
    ]

    buyer_name = models.CharField(max_length=255)
    buyer_phone = models.CharField(max_length=30)
    visit_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ISSUED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gate_ticket_sales_created",
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["club", "visit_date"]),
            models.Index(fields=["club", "status"]),
            models.Index(fields=["club", "buyer_phone"]),
            models.Index(fields=["club", "created_by"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Gate sale #{self.id} - {self.buyer_name}"


class GateTicket(TenantBaseModel):
    STATUS_ISSUED = "issued"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_VOIDED = "voided"
    STATUS_CHOICES = [
        (STATUS_ISSUED, "Issued"),
        (STATUS_CHECKED_IN, "Checked In"),
        (STATUS_VOIDED, "Voided"),
    ]

    sale = models.ForeignKey(GateTicketSale, on_delete=models.CASCADE, related_name="tickets")
    ticket_type = models.ForeignKey(
        GateTicketType,
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    visit_date = models.DateField()
    code = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ISSUED)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_tickets_checked_in",
    )

    class Meta:
        indexes = [
            models.Index(fields=["club", "visit_date"]),
            models.Index(fields=["club", "status"]),
            models.Index(fields=["club", "ticket_type"]),
            models.Index(fields=["code"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.ticket_type.name}"

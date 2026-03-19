from django.conf import settings
from django.db import models

from clubs.models import BaseModel, Club


class AuditLog(BaseModel):
    ACTION_CHOICES = [
        ("sale_created", "Sale Created"),
        ("sale_refunded", "Sale Refunded"),
        ("price_override", "Price Override"),
        ("stock_adjustment", "Stock Adjustment"),
        ("stock_restock", "Stock Restock"),
        ("stock_refund", "Stock Refund"),
        ("low_stock_alert_created", "Low Stock Alert Created"),
        ("occasion_type_created", "Occasion Type Created"),
        ("occasion_type_updated", "Occasion Type Updated"),
        ("occasion_type_deactivated", "Occasion Type Deactivated"),
        ("reservation_created", "Reservation Created"),
        ("reservation_payment_recorded", "Reservation Payment Recorded"),
        ("reservation_cancelled", "Reservation Cancelled"),
        ("reservation_refunded", "Reservation Refunded"),
        ("gate_ticket_type_created", "Gate Ticket Type Created"),
        ("gate_ticket_type_updated", "Gate Ticket Type Updated"),
        ("gate_ticket_type_deactivated", "Gate Ticket Type Deactivated"),
        ("gate_entry_day_created", "Gate Entry Day Created"),
        ("gate_entry_day_updated", "Gate Entry Day Updated"),
        ("gate_ticket_sale_created", "Gate Ticket Sale Created"),
        ("gate_ticket_checked_in", "Gate Ticket Checked In"),
        ("gate_ticket_voided", "Gate Ticket Voided"),
    ]

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "action"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.user_id or 'system'}"

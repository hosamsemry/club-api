from django.conf import settings
from django.db import models

from clubs.models import TenantBaseModel


class OccasionType(TenantBaseModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club", "name"],
                name="unique_occasion_type_name_per_club",
            )
        ]
        indexes = [
            models.Index(fields=["club", "is_active"]),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class VenueReservation(TenantBaseModel):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_PARTIAL = "partial"
    PAYMENT_PAID = "paid"
    PAYMENT_REFUNDED = "refunded"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_UNPAID, "Unpaid"),
        (PAYMENT_PARTIAL, "Partial"),
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_REFUNDED, "Refunded"),
    ]

    occasion_type = models.ForeignKey(
        OccasionType,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    guest_name = models.CharField(max_length=255)
    guest_phone = models.CharField(max_length=30)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    guest_count = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_UNPAID,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="venue_reservations_created",
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["club", "starts_at"]),
            models.Index(fields=["club", "ends_at"]),
            models.Index(fields=["club", "status"]),
            models.Index(fields=["club", "payment_status"]),
            models.Index(fields=["club", "occasion_type"]),
            models.Index(fields=["club", "guest_phone"]),
        ]
        ordering = ["-starts_at"]

    def __str__(self):
        return f"{self.guest_name} - {self.occasion_type.name}"

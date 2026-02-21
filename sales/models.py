from django.db import models
from django.conf import settings
from clubs.models import TenantBaseModel


class Sale(TenantBaseModel):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_created"
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")

    class Meta:
        indexes = [
            models.Index(fields=["club", "created_at"]),
            models.Index(fields=["club", "status"]),
        ]

    def __str__(self):
        return f"Sale #{self.id} ({self.total_amount})"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["sale"]),
            models.Index(fields=["product"]),
        ]
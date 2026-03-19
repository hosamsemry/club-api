from django.db import models
from clubs.models import TenantBaseModel
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db.models import CheckConstraint, Q

class Category(TenantBaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club", "name"], name="unique_category_name_per_club"
            )
        ]


class Product(TenantBaseModel):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    sku = models.CharField(max_length=50)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["club", "sku"], name="unique_sku_per_club"),
            models.UniqueConstraint(fields=["club", "name"], name="unique_product_name_per_club"),
            models.CheckConstraint(
                condition=Q(cost_price__gte=0),
                name="cost_price_positive"
            ),
            models.CheckConstraint(
                condition=Q(selling_price__gte=0),
                name="selling_price_positive"
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="stock_non_negative"
            ),
        ]
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["club", "category"]),
        ]
        ordering = ["-created_at"]


class StockMovement(TenantBaseModel):
    MOVEMENT_TYPES = [
        ("restock", "Restock"),
        ("sale", "Sale"),
        ("adjustment", "Adjustment"),
        ("refund", "Refund"),
    ]
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="movements"
    )
    movement_type = models.CharField(max_length=25, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "product"]),
            models.Index(fields=["club", "created_at"]),
        ]


    def __str__(self):
        user = self.created_by.username if self.created_by else "Unknown"
        return f"{self.product.name} - {self.movement_type} ({self.quantity}) by {user}"


class LowStockAlert(TenantBaseModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="low_stock_alerts"
    )
    triggered_by_movement = models.ForeignKey(
        StockMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_low_stock_alerts",
    )
    threshold_value = models.PositiveIntegerField()
    stock_quantity_at_trigger = models.PositiveIntegerField()
    recipient_user_ids = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["club", "product"]),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(threshold_value__gte=0),
                name="low_stock_threshold_value_non_negative",
            ),
            CheckConstraint(
                condition=Q(stock_quantity_at_trigger__gte=0),
                name="low_stock_quantity_at_trigger_non_negative",
            ),
        ]

    def __str__(self):
        return f"Low stock alert for {self.product.name} ({self.stock_quantity_at_trigger})"

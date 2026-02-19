from django.db import transaction
from rest_framework.exceptions import ValidationError
from inventory.models import Product, StockMovement


class StockService:

    @staticmethod
    @transaction.atomic
    def create_movement(*, product, movement_type, quantity, user, direction=None, note=""):
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        
        product = Product.objects.select_for_update().get(pk=product.pk)

        if product.stock_quantity < product.low_stock_threshold:
            # Optional: Log low stock warning or notify users
            pass

        if movement_type == "restock" or movement_type == "refund":
            delta = quantity

        elif movement_type == "sale":
            delta = -quantity

        elif movement_type == "adjustment":
            if direction not in ("in", "out"):
                raise ValidationError("Adjustment requires direction: 'in' or 'out'.")
            delta = quantity if direction == "in" else -quantity

        else:
            raise ValidationError("Invalid movement type.")

        if product.stock_quantity + delta < 0:
            raise ValidationError({"detail": f"Insufficient stock. Available: {product.stock_quantity}"})

        movement = StockMovement.objects.create(
            club=product.club,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            created_by=user,
            note=note,
        )

        product.stock_quantity += delta
        product.save(update_fields=["stock_quantity"])

        return movement

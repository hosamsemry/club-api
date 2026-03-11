from django.db import transaction
from rest_framework.exceptions import ValidationError
from core.services.audit_service import AuditService
from inventory.models import Product, StockMovement


class StockService:
    @staticmethod
    def _locked_product(*, product_id, club):
        return Product.objects.select_for_update().get(pk=product_id, club=club)

    @staticmethod
    @transaction.atomic
    def create_movement(
        *,
        product,
        movement_type,
        quantity,
        user,
        direction=None,
        note="",
        lock_product=True,
    ):

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        if lock_product:
            product = StockService._locked_product(product_id=product.pk, club=product.club)

        if movement_type in ("restock", "refund"):
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
            raise ValidationError(
                {"detail": f"Insufficient stock. Available: {product.stock_quantity}"}
            )

        movement = StockMovement.objects.create(
            club=product.club,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            created_by=user,
            note=note,
        )

        old_stock = product.stock_quantity
        product.stock_quantity += delta
        product.save(update_fields=["stock_quantity"])

        action_map = {
            "refund": "stock_refund",
            "restock": "stock_restock",
            "adjustment": "stock_adjustment",
        }

        if movement_type in action_map:
            AuditService.log(
                action=action_map[movement_type],
                club=product.club,
                user=user,
                details={
                    "product_id": product.id,
                    "product_name": product.name,
                    "movement_type": movement_type,
                    "direction": direction,
                    "quantity": quantity,
                    "old_stock": old_stock,
                    "new_stock": product.stock_quantity,
                    "note": note,
                },
            )
        return movement
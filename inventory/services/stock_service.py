from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from core.services.audit_service import AuditService
from inventory.models import Product, StockMovement, LowStockAlert


User = get_user_model()


class StockService:
    LOW_STOCK_RECIPIENT_ROLES = ("owner", "manager")

    @staticmethod
    def _locked_product(*, product_id, club):
        return Product.objects.select_for_update().get(pk=product_id, club=club)

    @staticmethod
    def _low_stock_recipient_ids(*, club):
        return list(
            User.objects.filter(
                club=club,
                is_active=True,
                role__in=StockService.LOW_STOCK_RECIPIENT_ROLES,
            )
            .order_by("id")
            .values_list("id", flat=True)
        )

    @staticmethod
    def _handle_low_stock_alert(*, product, movement, old_stock, new_stock, user):
        threshold = product.low_stock_threshold
        was_above_threshold = old_stock > threshold
        is_now_low_stock = new_stock <= threshold
        was_low_stock = old_stock <= threshold
        is_now_above_threshold = new_stock > threshold

        if was_above_threshold and is_now_low_stock:
            recipient_ids = StockService._low_stock_recipient_ids(club=product.club)
            LowStockAlert.objects.create(
                club=product.club,
                product=product,
                triggered_by_movement=movement,
                threshold_value=threshold,
                stock_quantity_at_trigger=new_stock,
                recipient_user_ids=recipient_ids,
            )
            AuditService.log(
                action="low_stock_alert_created",
                club=product.club,
                user=user,
                details={
                    "product_id": product.id,
                    "product_name": product.name,
                    "movement_id": movement.id,
                    "threshold_value": threshold,
                    "old_stock": old_stock,
                    "new_stock": new_stock,
                    "recipient_roles": list(StockService.LOW_STOCK_RECIPIENT_ROLES),
                    "recipient_user_ids": recipient_ids,
                },
            )

        if was_low_stock and is_now_above_threshold:
            LowStockAlert.objects.filter(
                club=product.club,
                product=product,
                is_active=True,
            ).update(is_active=False, resolved_at=timezone.now())

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
        new_stock = product.stock_quantity

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
                    "new_stock": new_stock,
                    "note": note,
                },
            )

        StockService._handle_low_stock_alert(
            product=product,
            movement=movement,
            old_stock=old_stock,
            new_stock=new_stock,
            user=user,
        )
        return movement

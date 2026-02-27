from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from inventory.models import Product
from inventory.services.stock_service import StockService
from sales.models import Sale, SaleItem


class SaleService:
    OVERRIDE_ROLES = {"owner", "manager"}

    @staticmethod
    @transaction.atomic
    def create_sale(*, club, user, items, note=""):
        if not items:
            raise ValidationError({"items": "Sale must contain at least one item."})

        qty_by_product_id = {}
        for row in items:
            product_id = row.get("product_id")
            quantity = row.get("quantity")

            if not product_id or quantity is None:
                raise ValidationError("Each item must include product_id and quantity.")
            if quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")

            qty_by_product_id[product_id] = qty_by_product_id.get(product_id, 0) + quantity

        product_ids = list(qty_by_product_id.keys())

        products = (
            Product.objects.select_for_update()
            .filter(club=club, id__in=product_ids)
            .order_by("id")
        )
        products_by_id = {p.id: p for p in products}

        if len(products_by_id) != len(product_ids):
            raise ValidationError("One or more products do not exist for this club.")

        for pid, required_qty in qty_by_product_id.items():
            product = products_by_id[pid]
            if product.stock_quantity < required_qty:
                raise ValidationError(
                    {"detail": f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}"}
                )

        sale = Sale.objects.create(
            club=club,
            created_by=user,
            total_amount=Decimal("0.00"),
        )

        total = Decimal("0.00")

        for row in items:
            product_id = row["product_id"]
            quantity = row["quantity"]
            unit_price_override = row.get("unit_price", None)

            product = products_by_id[product_id]
            default_price = product.selling_price

            if unit_price_override is None:
                unit_price = default_price
            else:
                if user.role not in SaleService.OVERRIDE_ROLES:
                    raise PermissionDenied("Only owner/manager can override prices.")
                unit_price = Decimal(str(unit_price_override))
                if unit_price < 0:
                    raise ValidationError("unit_price cannot be negative.")

            subtotal = unit_price * Decimal(quantity)

            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )

            total += subtotal

            StockService.create_movement(
                product=product,
                movement_type="sale",
                quantity=quantity,
                user=user,
                note=note or f"Sale #{sale.id}",
                lock_product=False,
            )

        sale.total_amount = total
        sale.save(update_fields=["total_amount"])

        return sale
    
    
    @staticmethod
    @transaction.atomic
    def refund_sale(*, club, user, sale_id, note=""):
        if user.role not in {"owner", "manager"}:
            raise PermissionDenied("Only owner/manager can refund sales.")

        sale = (
            Sale.objects.select_for_update()
            .select_related("club")
            .prefetch_related("items__product")
            .get(id=sale_id, club=club)
        )

        if sale.status != "completed":
            raise ValidationError({"detail": f"Only completed sales can be refunded. Current: {sale.status}."})

        product_ids = [item.product_id for item in sale.items.all()]

        products = (
            Product.objects.select_for_update()
            .filter(club=club, id__in=product_ids)
            .order_by("id")
        )
        products_by_id = {p.id: p for p in products}

        for item in sale.items.all():
            product = products_by_id[item.product_id]

            StockService.create_movement(
                product=product,
                movement_type="refund",
                quantity=item.quantity,
                user=user,
                note=note or f"Refund Sale #{sale.id}",
                lock_product=False,
            )

        sale.status = "refunded"
        sale.save(update_fields=["status"])

        return sale
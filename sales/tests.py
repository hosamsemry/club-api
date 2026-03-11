from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from clubs.models import Club
from core.models import AuditLog
from inventory.models import Category, Product, StockMovement
from sales.models import Sale
from sales.services.sale_service import SaleService


User = get_user_model()


class SaleServiceTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Test Club")
        self.category = Category.objects.create(club=self.club, name="Drinks")
        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Water",
            sku="WATER-1",
            cost_price=Decimal("5.00"),
            selling_price=Decimal("10.00"),
            stock_quantity=20,
        )

    def test_cashier_can_create_sale_when_client_sends_default_unit_price(self):
        cashier = User.objects.create_user(
            email="cashier@example.com",
            username="cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )

        sale = SaleService.create_sale(
            club=self.club,
            user=cashier,
            items=[
                {
                    "product_id": self.product.id,
                    "quantity": 2,
                    "unit_price": "10.00",
                }
            ],
            note="POS checkout",
        )

        self.product.refresh_from_db()

        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(sale.total_amount, Decimal("20.00"))
        self.assertEqual(self.product.stock_quantity, 18)
        self.assertEqual(StockMovement.objects.filter(movement_type="sale").count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="sale_created").exists())

    def test_cashier_cannot_override_default_price(self):
        cashier = User.objects.create_user(
            email="cashier2@example.com",
            username="cashier2",
            password="secret123",
            club=self.club,
            role="cashier",
        )

        with self.assertRaisesMessage(PermissionDenied, "Only owner/manager can override prices."):
            SaleService.create_sale(
                club=self.club,
                user=cashier,
                items=[
                    {
                        "product_id": self.product.id,
                        "quantity": 1,
                        "unit_price": "9.50",
                    }
                ],
            )

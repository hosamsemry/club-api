from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from clubs.models import Club
from core.models import AuditLog
from inventory.models import Category, Product, LowStockAlert
from inventory.services.stock_service import StockService


User = get_user_model()


class LowStockAlertServiceTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Test Club")
        self.category = Category.objects.create(club=self.club, name="Snacks")
        self.owner = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            username="manager",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="cashier@example.com",
            username="cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Chips",
            sku="CHIPS-1",
            cost_price=Decimal("5.00"),
            selling_price=Decimal("10.00"),
            stock_quantity=12,
            low_stock_threshold=10,
        )

    def test_creates_alert_when_stock_hits_threshold(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=2,
            user=self.cashier,
        )

        self.product.refresh_from_db()
        alert = LowStockAlert.objects.get(product=self.product)

        self.assertEqual(self.product.stock_quantity, 10)
        self.assertTrue(alert.is_active)
        self.assertEqual(alert.threshold_value, 10)
        self.assertEqual(alert.stock_quantity_at_trigger, 10)
        self.assertEqual(alert.recipient_user_ids, [self.owner.id, self.manager.id])
        self.assertTrue(
            AuditLog.objects.filter(
                action="low_stock_alert_created",
                details__product_id=self.product.id,
            ).exists()
        )

    def test_creates_alert_when_stock_drops_below_threshold(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=3,
            user=self.cashier,
        )

        alert = LowStockAlert.objects.get(product=self.product)

        self.assertEqual(alert.stock_quantity_at_trigger, 9)
        self.assertTrue(alert.is_active)

    def test_does_not_create_duplicate_alerts_while_stock_stays_low(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=2,
            user=self.cashier,
        )
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=1,
            user=self.cashier,
        )

        self.assertEqual(LowStockAlert.objects.filter(product=self.product).count(), 1)

    def test_resolves_alert_after_restock_above_threshold(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=3,
            user=self.cashier,
        )

        StockService.create_movement(
            product=self.product,
            movement_type="restock",
            quantity=5,
            user=self.manager,
        )

        alert = LowStockAlert.objects.get(product=self.product)
        self.product.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, 14)
        self.assertFalse(alert.is_active)
        self.assertIsNotNone(alert.resolved_at)

    def test_creates_new_alert_after_restock_and_drop_again(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=2,
            user=self.cashier,
        )
        StockService.create_movement(
            product=self.product,
            movement_type="restock",
            quantity=5,
            user=self.manager,
        )
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=7,
            user=self.cashier,
        )

        alerts = list(LowStockAlert.objects.filter(product=self.product).order_by("created_at"))

        self.assertEqual(len(alerts), 2)
        self.assertFalse(alerts[0].is_active)
        self.assertTrue(alerts[1].is_active)

    def test_no_alert_when_movement_does_not_cross_threshold(self):
        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=1,
            user=self.cashier,
        )

        self.assertFalse(LowStockAlert.objects.exists())


class LowStockAlertApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.club = Club.objects.create(name="Main Club")
        self.other_club = Club.objects.create(name="Other Club")
        self.category = Category.objects.create(club=self.club, name="Snacks")
        self.other_category = Category.objects.create(club=self.other_club, name="Drinks")

        self.owner = User.objects.create_user(
            email="owner@club.com",
            username="owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="manager@club.com",
            username="manager",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="cashier@club.com",
            username="cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.other_owner = User.objects.create_user(
            email="owner@otherclub.com",
            username="other-owner",
            password="secret123",
            club=self.other_club,
            role="owner",
        )

        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Cookies",
            sku="COOKIE-1",
            cost_price=Decimal("4.00"),
            selling_price=Decimal("8.00"),
            stock_quantity=11,
            low_stock_threshold=10,
        )
        self.other_product = Product.objects.create(
            club=self.other_club,
            category=self.other_category,
            name="Juice",
            sku="JUICE-1",
            cost_price=Decimal("3.00"),
            selling_price=Decimal("7.00"),
            stock_quantity=10,
            low_stock_threshold=10,
        )

        StockService.create_movement(
            product=self.product,
            movement_type="sale",
            quantity=1,
            user=self.cashier,
        )
        other_manager = User.objects.create_user(
            email="manager@otherclub.com",
            username="other-manager",
            password="secret123",
            club=self.other_club,
            role="manager",
        )
        StockService.create_movement(
            product=self.other_product,
            movement_type="sale",
            quantity=1,
            user=other_manager,
        )

    def test_owner_can_list_only_current_club_alerts(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/inventory/low-stock-alerts/")
        results = response.data["results"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["product"], self.product.id)
        self.assertEqual(
            [user["role"] for user in results[0]["recipient_users"]],
            ["owner", "manager"],
        )

    def test_manager_can_filter_active_alerts_by_product(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            f"/api/inventory/low-stock-alerts/?is_active=True&product={self.product.id}"
        )
        results = response.data["results"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_active"])

    def test_cashier_cannot_access_low_stock_alert_list(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.get("/api/inventory/low-stock-alerts/")

        self.assertEqual(response.status_code, 403)

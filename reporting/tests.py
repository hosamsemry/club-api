from datetime import datetime, date, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from clubs.models import Club
from core.models import AuditLog
from inventory.models import Category, Product
from reporting.models import DailyClubReport
from reporting.services.daily_report_service import DailyReportService
from sales.models import Sale
from sales.services.sale_service import SaleService


User = get_user_model()


class DailyReportServiceTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Cairo Club", timezone="Africa/Cairo")
        self.category = Category.objects.create(club=self.club, name="Drinks")
        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Water",
            sku="WATER-1",
            cost_price=Decimal("5.00"),
            selling_price=Decimal("10.00"),
            stock_quantity=50,
        )
        self.owner = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="secret123",
            club=self.club,
            role="owner",
        )

    def test_generates_report_for_requested_local_date(self):
        sale = SaleService.create_sale(
            club=self.club,
            user=self.owner,
            items=[{"product_id": self.product.id, "quantity": 2}],
            note="Morning sale",
        )
        Sale.objects.filter(pk=sale.pk).update(
            created_at=datetime(2026, 3, 10, 7, 0, tzinfo=dt_timezone.utc)
        )
        AuditLog.objects.filter(action="sale_created", details__sale_id=sale.id).update(
            created_at=datetime(2026, 3, 10, 7, 5, tzinfo=dt_timezone.utc)
        )

        report = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 10),
        )

        self.assertIsInstance(report, DailyClubReport)
        self.assertEqual(report.sales_count, 1)
        self.assertEqual(report.total_revenue, Decimal("20.00"))
        self.assertEqual(report.audit_action_counts["sale_created"], 1)

    def test_refund_reduces_revenue_on_refund_day(self):
        sale = SaleService.create_sale(
            club=self.club,
            user=self.owner,
            items=[{"product_id": self.product.id, "quantity": 1}],
        )
        Sale.objects.filter(pk=sale.pk).update(
            created_at=datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc),
            refunded_at=datetime(2026, 3, 11, 10, 0, tzinfo=dt_timezone.utc),
            status="refunded",
        )
        refund_log = AuditLog.objects.create(
            action="sale_refunded",
            club=self.club,
            user=self.owner,
            details={"sale_id": sale.id},
        )
        AuditLog.objects.filter(pk=refund_log.pk).update(
            created_at=datetime(2026, 3, 11, 10, 5, tzinfo=dt_timezone.utc)
        )

        sale_day_report = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 10),
        )
        refund_day_report = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 11),
        )

        self.assertEqual(sale_day_report.total_revenue, Decimal("10.00"))
        self.assertEqual(refund_day_report.total_revenue, Decimal("-10.00"))
        self.assertEqual(refund_day_report.audit_action_counts["sale_refunded"], 1)

    def test_regeneration_updates_existing_report(self):
        report = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 10),
        )

        AuditLog.objects.create(
            action="stock_restock",
            club=self.club,
            user=self.owner,
            details={"product_id": self.product.id},
        )

        regenerated = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 10),
        )

        self.assertEqual(report.pk, regenerated.pk)

    def test_inactive_club_does_not_get_report(self):
        self.club.is_active = False
        self.club.save(update_fields=["is_active"])

        with self.assertRaisesMessage(ValueError, "Inactive clubs do not receive daily reports."):
            DailyReportService.generate_for_club(
                club=self.club,
                report_date=date(2026, 3, 10),
            )

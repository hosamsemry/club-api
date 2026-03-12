from datetime import datetime, date, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from clubs.models import Club
from core.models import AuditLog
from inventory.models import Category, Product
from reporting.models import DailyClubReport
from reporting.services.daily_report_service import DailyReportService
from reporting.services.export_service import ReportExportService
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

    def test_pending_report_date_returns_yesterday_after_cutoff(self):
        pending_date = DailyReportService.get_pending_report_date(
            club=self.club,
            now=datetime(2026, 3, 12, 3, 15, tzinfo=dt_timezone.utc),
            cutoff_minutes=5,
        )

        self.assertEqual(pending_date, date(2026, 3, 11))

    def test_pending_report_date_skips_existing_report(self):
        DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 11),
        )

        pending_date = DailyReportService.get_pending_report_date(
            club=self.club,
            now=datetime(2026, 3, 12, 3, 15, tzinfo=dt_timezone.utc),
            cutoff_minutes=5,
        )

        self.assertIsNone(pending_date)


class DailyClubReportViewSetTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Main Club", timezone="UTC")
        self.other_club = Club.objects.create(name="Other Club", timezone="UTC")
        self.owner = User.objects.create_user(
            email="owner@reports.com",
            username="owner_reports",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.cashier = User.objects.create_user(
            email="cashier@reports.com",
            username="cashier_reports",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.report = DailyClubReport.objects.create(
            club=self.club,
            report_date=date(2026, 3, 11),
            timezone="UTC",
            source_window_start=datetime(2026, 3, 11, 0, 0, tzinfo=dt_timezone.utc),
            source_window_end=datetime(2026, 3, 12, 0, 0, tzinfo=dt_timezone.utc),
            sales_count=3,
            total_revenue=Decimal("120.00"),
            audit_action_counts={"sale_created": 3},
        )
        self.other_report = DailyClubReport.objects.create(
            club=self.other_club,
            report_date=date(2026, 3, 11),
            timezone="UTC",
            source_window_start=datetime(2026, 3, 11, 0, 0, tzinfo=dt_timezone.utc),
            source_window_end=datetime(2026, 3, 12, 0, 0, tzinfo=dt_timezone.utc),
            sales_count=1,
            total_revenue=Decimal("50.00"),
            audit_action_counts={"sale_created": 1},
        )

    def test_owner_can_list_only_club_reports(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("dailyclubreport-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.report.id)

    def test_cashier_cannot_access_reports(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.get(reverse("dailyclubreport-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_csv_generates_file_on_request(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("dailyclubreport-export-csv", args=[self.report.id]))

        self.report.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.report.csv_file.name.endswith(".csv"))

    def test_regeneration_clears_previous_csv_export(self):
        ReportExportService.generate_csv(report=self.report)
        self.assertTrue(self.report.csv_file.name)

        self.report.total_revenue = Decimal("140.00")
        self.report.save(update_fields=["total_revenue"])

        regenerated = DailyReportService.regenerate_for_club(
            club=self.club,
            report_date=self.report.report_date,
        )

        self.assertEqual(regenerated.pk, self.report.pk)
        self.assertFalse(bool(regenerated.csv_file))

    def test_pending_report_date_skips_before_local_cutoff(self):
        pending_date = DailyReportService.get_pending_report_date(
            club=self.club,
            now=datetime(2026, 3, 11, 22, 2, tzinfo=dt_timezone.utc),
            cutoff_minutes=5,
        )

        self.assertIsNone(pending_date)

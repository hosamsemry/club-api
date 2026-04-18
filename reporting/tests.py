from datetime import datetime, date, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from clubs.models import Club
from core.models import AuditLog
from events.models import OccasionType, VenueReservation
from inventory.models import Category, Product
from reporting.models import DailyClubReport
from reporting.services.daily_report_service import DailyReportService
from reporting.services.export_service import ReportExportService
from reporting.services.revenue_range_service import RevenueRangeService
from sales.models import Sale
from sales.services.sale_service import SaleService
from tickets.models import GateTicket, GateTicketSale, GateTicketType


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
        self.occasion_type = OccasionType.objects.create(club=self.club, name="Wedding")
        self.ticket_type = GateTicketType.objects.create(
            club=self.club,
            name="Adult",
            price=Decimal("50.00"),
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
        ticket_sale = GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Ticket Buyer",
            buyer_phone="01000000000",
            visit_date=date(2026, 3, 10),
            total_amount=Decimal("100.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.owner,
        )
        GateTicketSale.objects.filter(pk=ticket_sale.pk).update(
            created_at=datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc)
        )
        ticket = GateTicket.objects.create(
            club=self.club,
            sale=ticket_sale,
            ticket_type=self.ticket_type,
            visit_date=date(2026, 3, 10),
            code="TICKET-0001",
            status=GateTicket.STATUS_CHECKED_IN,
            checked_in_at=datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc),
            checked_in_by=self.owner,
        )
        GateTicket.objects.filter(pk=ticket.pk).update(
            created_at=datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc)
        )
        VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Ahmed",
            guest_phone="01000000001",
            starts_at=datetime(2026, 3, 10, 18, 0, tzinfo=dt_timezone.utc),
            ends_at=datetime(2026, 3, 10, 22, 0, tzinfo=dt_timezone.utc),
            guest_count=120,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("300.00"),
            status=VenueReservation.STATUS_CONFIRMED,
            created_by=self.owner,
        )

        report = DailyReportService.generate_for_club(
            club=self.club,
            report_date=date(2026, 3, 10),
        )

        self.assertIsInstance(report, DailyClubReport)
        self.assertEqual(report.sales_count, 1)
        self.assertEqual(report.total_revenue, Decimal("20.00"))
        self.assertEqual(report.audit_action_counts["sale_created"], 1)
        self.assertEqual(report.revenue_breakdown["products"], "20.00")
        self.assertEqual(report.revenue_breakdown["tickets"], "100.00")
        self.assertEqual(report.revenue_breakdown["events"], "300.00")
        self.assertEqual(report.revenue_breakdown["total_revenue"], "420.00")
        self.assertEqual(report.activity_summary["items_sold"], 2)
        self.assertEqual(report.activity_summary["tickets_checked_in"], 1)
        self.assertEqual(report.activity_summary["event_reservations_count"], 1)
        self.assertEqual(report.activity_summary["event_guest_count"], 120)
        self.assertEqual(report.activity_summary["average_sale_value"], "20.00")
        self.assertEqual(len(report.top_products), 1)
        self.assertEqual(report.top_products[0]["product_name"], "Water")
        self.assertEqual(report.top_products[0]["total_quantity_sold"], 2)

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
        self.assertIn("revenue_breakdown", response.data["results"][0])
        self.assertIn("activity_summary", response.data["results"][0])
        self.assertIn("top_products", response.data["results"][0])

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
            now=datetime(2026, 3, 11, 0, 2, tzinfo=dt_timezone.utc),
            cutoff_minutes=5,
        )

        self.assertIsNone(pending_date)


# ── Revenue Range Service & Endpoint Tests ──────────────────────────────────


class RevenueRangeServiceTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Revenue Club", timezone="UTC")
        self.category = Category.objects.create(club=self.club, name="Drinks")
        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Soda",
            sku="SODA-1",
            cost_price=Decimal("3.00"),
            selling_price=Decimal("8.00"),
            stock_quantity=100,
        )
        self.owner = User.objects.create_user(
            email="rev_owner@example.com",
            username="rev_owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.occasion_type = OccasionType.objects.create(club=self.club, name="Party")

    def _create_sale(self, created_at, amount, sale_status="completed", refunded_at=None):
        sale = Sale.objects.create(
            club=self.club,
            created_by=self.owner,
            total_amount=amount,
            status=sale_status,
            refunded_at=refunded_at,
        )
        Sale.objects.filter(pk=sale.pk).update(created_at=created_at, refunded_at=refunded_at)
        return sale

    def _create_ticket_sale(self, created_at, amount, sale_status=GateTicketSale.STATUS_ISSUED):
        ts = GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Buyer",
            buyer_phone="01000000000",
            visit_date=created_at.date(),
            total_amount=amount,
            status=sale_status,
            created_by=self.owner,
        )
        GateTicketSale.objects.filter(pk=ts.pk).update(created_at=created_at)
        return ts

    def _create_reservation(self, starts_at, total, paid, res_status="confirmed"):
        return VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Guest",
            guest_phone="01000000001",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=4),
            guest_count=50,
            total_amount=total,
            paid_amount=paid,
            status=res_status,
            created_by=self.owner,
        )

    def test_single_field_products(self):
        self._create_sale(datetime(2026, 3, 10, 12, 0, tzinfo=dt_timezone.utc), Decimal("100.00"))
        self._create_sale(datetime(2026, 3, 11, 12, 0, tzinfo=dt_timezone.utc), Decimal("50.00"))

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 11),
            fields=["products"],
        )

        self.assertEqual(result["products"], Decimal("150.00"))
        self.assertEqual(result["total_revenue"], Decimal("150.00"))
        self.assertNotIn("tickets", result)
        self.assertNotIn("events", result)

    def test_single_field_tickets(self):
        self._create_ticket_sale(datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc), Decimal("200.00"))
        self._create_ticket_sale(
            datetime(2026, 3, 10, 11, 0, tzinfo=dt_timezone.utc),
            Decimal("999.00"),
            sale_status=GateTicketSale.STATUS_VOIDED,
        )

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
            fields=["tickets"],
        )

        self.assertEqual(result["tickets"], Decimal("200.00"))
        self.assertEqual(result["total_revenue"], Decimal("200.00"))

    def test_single_field_events(self):
        self._create_reservation(
            datetime(2026, 3, 10, 18, 0, tzinfo=dt_timezone.utc),
            total=Decimal("5000.00"),
            paid=Decimal("3000.00"),
        )
        # cancelled reservation should be excluded
        self._create_reservation(
            datetime(2026, 3, 10, 20, 0, tzinfo=dt_timezone.utc),
            total=Decimal("2000.00"),
            paid=Decimal("1000.00"),
            res_status="cancelled",
        )

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
            fields=["events"],
        )

        self.assertEqual(result["events"], Decimal("3000.00"))
        self.assertEqual(result["total_revenue"], Decimal("3000.00"))

    def test_multi_field_total(self):
        self._create_sale(datetime(2026, 3, 10, 12, 0, tzinfo=dt_timezone.utc), Decimal("100.00"))
        self._create_ticket_sale(datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc), Decimal("200.00"))
        self._create_reservation(
            datetime(2026, 3, 10, 18, 0, tzinfo=dt_timezone.utc),
            total=Decimal("5000.00"),
            paid=Decimal("3000.00"),
        )

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
            fields=["products", "tickets", "events"],
        )

        self.assertEqual(result["products"], Decimal("100.00"))
        self.assertEqual(result["tickets"], Decimal("200.00"))
        self.assertEqual(result["events"], Decimal("3000.00"))
        self.assertEqual(result["total_revenue"], Decimal("3300.00"))

    def test_products_refund_is_subtracted(self):
        self._create_sale(datetime(2026, 3, 10, 12, 0, tzinfo=dt_timezone.utc), Decimal("100.00"))
        self._create_sale(
            datetime(2026, 3, 9, 12, 0, tzinfo=dt_timezone.utc),
            Decimal("50.00"),
            sale_status="refunded",
            refunded_at=datetime(2026, 3, 10, 14, 0, tzinfo=dt_timezone.utc),
        )

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
            fields=["products"],
        )

        self.assertEqual(result["products"], Decimal("50.00"))

    def test_date_boundary_inclusive(self):
        """Data exactly on start and end dates should be included."""
        self._create_sale(datetime(2026, 3, 10, 0, 0, tzinfo=dt_timezone.utc), Decimal("10.00"))
        self._create_sale(datetime(2026, 3, 12, 23, 59, 59, tzinfo=dt_timezone.utc), Decimal("20.00"))
        # just outside the range
        self._create_sale(datetime(2026, 3, 13, 0, 0, tzinfo=dt_timezone.utc), Decimal("999.00"))

        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 12),
            fields=["products"],
        )

        self.assertEqual(result["products"], Decimal("30.00"))

    def test_empty_range_returns_zero(self):
        result = RevenueRangeService.calculate(
            club=self.club,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            fields=["products", "tickets", "events"],
        )

        self.assertEqual(result["products"], Decimal("0.00"))
        self.assertEqual(result["tickets"], Decimal("0.00"))
        self.assertEqual(result["events"], Decimal("0.00"))
        self.assertEqual(result["total_revenue"], Decimal("0.00"))


class TransactionsViewSetTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Transactions Club", timezone="UTC")
        self.other_club = Club.objects.create(name="Other Transactions Club", timezone="UTC")
        self.owner = User.objects.create_user(
            email="transactions_owner@example.com",
            username="transactions_owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="transactions_manager@example.com",
            username="transactions_manager",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="transactions_cashier@example.com",
            username="transactions_cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.occasion_type = OccasionType.objects.create(club=self.club, name="Conference")
        self.url = reverse("transactions-list")
        self.export_url = reverse("transactions-export-csv")

    def _create_sale(self, created_at, amount, sale_status="completed", refunded_at=None):
        sale = Sale.objects.create(
            club=self.club,
            created_by=self.owner,
            total_amount=amount,
            status=sale_status,
            refunded_at=refunded_at,
        )
        Sale.objects.filter(pk=sale.pk).update(created_at=created_at, refunded_at=refunded_at)
        return sale

    def _create_ticket_sale(self, created_at, amount, sale_status=GateTicketSale.STATUS_ISSUED, buyer_name="Ticket Buyer"):
        ticket_sale = GateTicketSale.objects.create(
            club=self.club,
            buyer_name=buyer_name,
            buyer_phone="01000000000",
            visit_date=created_at.date(),
            total_amount=amount,
            status=sale_status,
            created_by=self.owner,
        )
        GateTicketSale.objects.filter(pk=ticket_sale.pk).update(created_at=created_at)
        return ticket_sale

    def _create_reservation(
        self,
        created_at,
        *,
        total_amount=Decimal("500.00"),
        paid_amount=Decimal("300.00"),
        refunded_amount=Decimal("0.00"),
        reservation_status=VenueReservation.STATUS_CONFIRMED,
        payment_status=VenueReservation.PAYMENT_PAID,
        refunded_at=None,
    ):
        reservation = VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Event Guest",
            guest_phone="01000000001",
            starts_at=created_at + timedelta(days=1),
            ends_at=created_at + timedelta(days=1, hours=4),
            guest_count=120,
            total_amount=total_amount,
            paid_amount=paid_amount,
            refunded_amount=refunded_amount,
            status=reservation_status,
            payment_status=payment_status,
            refunded_at=refunded_at,
            created_by=self.owner,
        )
        VenueReservation.objects.filter(pk=reservation.pk).update(created_at=created_at, refunded_at=refunded_at)
        return reservation

    def test_owner_can_list_combined_transactions(self):
        self._create_sale(datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc), Decimal("100.00"))
        self._create_ticket_sale(datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc), Decimal("150.00"))
        self._create_reservation(datetime(2026, 3, 10, 11, 0, tzinfo=dt_timezone.utc))
        self._create_sale(
            datetime(2026, 3, 8, 12, 0, tzinfo=dt_timezone.utc),
            Decimal("80.00"),
            sale_status="refunded",
            refunded_at=datetime(2026, 3, 10, 12, 30, tzinfo=dt_timezone.utc),
        )
        Sale.objects.create(
            club=self.other_club,
            created_by=self.owner,
            total_amount=Decimal("999.00"),
            status="completed",
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(
            {row["source"] for row in response.data["results"]},
            {"products", "tickets", "events"},
        )
        self.assertEqual(response.data["results"][0]["status"], "refunded")

    def test_filters_by_source_and_search(self):
        self._create_ticket_sale(
            datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc),
            Decimal("150.00"),
            buyer_name="Mariam",
        )
        self._create_ticket_sale(
            datetime(2026, 3, 10, 12, 0, tzinfo=dt_timezone.utc),
            Decimal("75.00"),
            buyer_name="Omar",
        )

        self.client.force_authenticate(self.manager)
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "source": "tickets",
                "search": "mariam",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["customer_name"], "Mariam")
        self.assertEqual(response.data["results"][0]["source"], "tickets")

    def test_cashier_cannot_access_transactions(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_csv_returns_downloadable_file(self):
        self._create_sale(datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc), Decimal("100.00"))
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.export_url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("transactions-2026-03-10-to-2026-03-10.csv", response["Content-Disposition"])


class RevenueViewSetTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="API Revenue Club", timezone="UTC")
        self.category = Category.objects.create(club=self.club, name="Food")
        self.product = Product.objects.create(
            club=self.club,
            category=self.category,
            name="Burger",
            sku="BURG-1",
            cost_price=Decimal("5.00"),
            selling_price=Decimal("15.00"),
            stock_quantity=50,
        )
        self.owner = User.objects.create_user(
            email="rev_api_owner@example.com",
            username="rev_api_owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="rev_api_manager@example.com",
            username="rev_api_manager",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="rev_api_cashier@example.com",
            username="rev_api_cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.url = reverse("revenue-list")

    def test_owner_can_query_revenue(self):
        sale = Sale.objects.create(
            club=self.club,
            created_by=self.owner,
            total_amount=Decimal("100.00"),
            status="completed",
        )
        Sale.objects.filter(pk=sale.pk).update(
            created_at=datetime(2026, 3, 10, 12, 0, tzinfo=dt_timezone.utc)
        )
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10", "fields": "products"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["products"]), Decimal("100.00"))
        self.assertEqual(Decimal(response.data["total_revenue"]), Decimal("100.00"))

    def test_manager_can_query_revenue(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10", "fields": "products"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cashier_cannot_access_revenue(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10", "fields": "products"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_fields_returns_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_field_value_returns_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10", "fields": "invalid"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_date_before_start_date_returns_400(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-12", "end_date": "2026-03-10", "fields": "products"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_fields_returned(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(
            self.url,
            {"start_date": "2026-03-10", "end_date": "2026-03-10", "fields": ["products", "tickets"]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)
        self.assertIn("tickets", response.data)
        self.assertIn("total_revenue", response.data)

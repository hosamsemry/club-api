from datetime import datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Sum

from events.models import VenueReservation
from sales.models import Sale
from tickets.models import GateTicketSale


class RevenueRangeService:
    """
    Compute revenue for one or more categories (tickets, products, events)
    over an inclusive [start_date, end_date] window interpreted in the
    club's local timezone.
    """

    @staticmethod
    def _get_utc_window(*, club, start_date, end_date):
        """Return (utc_start, utc_end) covering the inclusive local-date range."""
        tz = ZoneInfo(club.timezone or "UTC")
        local_start = datetime.combine(start_date, time.min, tzinfo=tz)
        # end_date inclusive → go to start of the next day
        local_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
        return (
            local_start.astimezone(dt_timezone.utc),
            local_end.astimezone(dt_timezone.utc),
        )

    # ── category helpers ────────────────────────────────────────────────

    @staticmethod
    def _products_revenue(*, club, utc_start, utc_end):
        """Net product sales revenue: completed sales minus refunds in the window."""
        created_total = (
            Sale.objects.filter(
                club=club,
                created_at__gte=utc_start,
                created_at__lt=utc_end,
            )
            .exclude(status="cancelled")
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        refunded_total = (
            Sale.objects.filter(
                club=club,
                refunded_at__gte=utc_start,
                refunded_at__lt=utc_end,
                status="refunded",
            ).aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        return created_total - refunded_total

    @staticmethod
    def _tickets_revenue(*, club, utc_start, utc_end):
        """Issued gate-ticket-sale revenue in the window (excludes voided)."""
        return (
            GateTicketSale.objects.filter(
                club=club,
                created_at__gte=utc_start,
                created_at__lt=utc_end,
                status=GateTicketSale.STATUS_ISSUED,
            ).aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

    @staticmethod
    def _events_revenue(*, club, utc_start, utc_end):
        """Paid amount of reservations whose starts_at falls in the window."""
        return (
            VenueReservation.objects.filter(
                club=club,
                starts_at__gte=utc_start,
                starts_at__lt=utc_end,
            )
            .exclude(status=VenueReservation.STATUS_CANCELLED)
            .aggregate(total=Sum("paid_amount"))["total"]
            or Decimal("0.00")
        )

    # ── dispatch map ────────────────────────────────────────────────────

    _CATEGORY_CALCULATORS = {
        "products": _products_revenue.__func__,
        "tickets": _tickets_revenue.__func__,
        "events": _events_revenue.__func__,
    }

    # ── public API ──────────────────────────────────────────────────────

    @classmethod
    def calculate(cls, *, club, start_date, end_date, fields):
        """
        Return a dict with per-category revenue and ``total_revenue``.

        Parameters
        ----------
        club : Club
        start_date, end_date : date  (inclusive)
        fields : list[str]  (subset of "tickets", "products", "events")
        """
        utc_start, utc_end = cls._get_utc_window(
            club=club, start_date=start_date, end_date=end_date,
        )

        result = {
            "start_date": start_date,
            "end_date": end_date,
        }
        total = Decimal("0.00")

        for field in fields:
            calculator = cls._CATEGORY_CALCULATORS[field]
            amount = calculator(club=club, utc_start=utc_start, utc_end=utc_end)
            result[field] = amount
            total += amount

        result["total_revenue"] = total
        return result

from datetime import datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from core.models import AuditLog
from reporting.models import DailyClubReport
from sales.models import Sale


class DailyReportService:
    @staticmethod
    def _get_club_timezone(club):
        return ZoneInfo(club.timezone or "UTC")

    @staticmethod
    def _get_report_window(*, club, report_date=None):
        tz = DailyReportService._get_club_timezone(club)

        if report_date is None:
            report_date = timezone.now().astimezone(tz).date() - timedelta(days=1)

        start_local = datetime.combine(report_date, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)

        return report_date, start_local.astimezone(dt_timezone.utc), end_local.astimezone(dt_timezone.utc)

    @staticmethod
    def _sales_count(*, club, window_start, window_end):
        return Sale.objects.filter(
            club=club,
            created_at__gte=window_start,
            created_at__lt=window_end,
        ).exclude(status="cancelled").count()

    @staticmethod
    def _total_revenue(*, club, window_start, window_end):
        created_sales_total = (
            Sale.objects.filter(
                club=club,
                created_at__gte=window_start,
                created_at__lt=window_end,
            )
            .exclude(status="cancelled")
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        refunded_sales_total = (
            Sale.objects.filter(
                club=club,
                refunded_at__gte=window_start,
                refunded_at__lt=window_end,
                status="refunded",
            ).aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        return created_sales_total - refunded_sales_total

    @staticmethod
    def _audit_action_counts(*, club, window_start, window_end):
        action_rows = (
            AuditLog.objects.filter(
                club=club,
                created_at__gte=window_start,
                created_at__lt=window_end,
            )
            .values("action")
            .annotate(count=Count("id"))
            .order_by("action")
        )

        return {row["action"]: row["count"] for row in action_rows}

    @staticmethod
    @transaction.atomic
    def generate_for_club(*, club, report_date=None):
        if not club.is_active:
            raise ValueError("Inactive clubs do not receive daily reports.")

        report_date, window_start, window_end = DailyReportService._get_report_window(
            club=club, report_date=report_date
        )

        report, _ = DailyClubReport.objects.update_or_create(
            club=club,
            report_date=report_date,
            defaults={
                "timezone": club.timezone or "UTC",
                "source_window_start": window_start,
                "source_window_end": window_end,
                "sales_count": DailyReportService._sales_count(
                    club=club, window_start=window_start, window_end=window_end
                ),
                "total_revenue": DailyReportService._total_revenue(
                    club=club, window_start=window_start, window_end=window_end
                ),
                "audit_action_counts": DailyReportService._audit_action_counts(
                    club=club, window_start=window_start, window_end=window_end
                ),
            },
        )

        return report

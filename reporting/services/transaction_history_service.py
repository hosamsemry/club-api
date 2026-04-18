from datetime import datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Q

from events.models import VenueReservation
from sales.models import Sale
from tickets.models import GateTicketSale


class UnifiedTransactionsService:
    """Build a normalized, cross-module transaction history for reporting/export."""

    @staticmethod
    def _get_utc_window(*, club, start_date, end_date):
        tz = ZoneInfo(club.timezone or "UTC")
        local_start = datetime.combine(start_date, time.min, tzinfo=tz)
        local_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
        return (
            local_start.astimezone(dt_timezone.utc),
            local_end.astimezone(dt_timezone.utc),
        )

    @staticmethod
    def _money(value):
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @classmethod
    def _product_rows(cls, *, club, utc_start, utc_end):
        sales = (
            Sale.objects.filter(club=club)
            .filter(
                Q(created_at__gte=utc_start, created_at__lt=utc_end)
                | Q(refunded_at__gte=utc_start, refunded_at__lt=utc_end)
            )
            .select_related("created_by")
            .prefetch_related("items__product")
        )

        rows = []
        for sale in sales:
            is_refund_event = (
                sale.status == "refunded"
                and sale.refunded_at is not None
                and utc_start <= sale.refunded_at < utc_end
            )
            activity_at = sale.refunded_at if is_refund_event else sale.created_at
            gross_amount = cls._money(sale.total_amount)
            refund_amount = gross_amount if is_refund_event else Decimal("0.00")
            if sale.status == "cancelled":
                net_amount = Decimal("0.00")
            elif is_refund_event:
                net_amount = -gross_amount
            else:
                net_amount = gross_amount

            item_parts = [f"{item.quantity}× {item.product.name}" for item in sale.items.all()]
            summary = ", ".join(item_parts[:2]) if item_parts else "Product sale"
            if len(item_parts) > 2:
                summary = f"{summary} +{len(item_parts) - 2} more"

            rows.append(
                {
                    "id": f"products-{sale.id}",
                    "source": "products",
                    "transaction_id": sale.id,
                    "reference": f"SALE-{sale.id}",
                    "activity_at": activity_at,
                    "status": sale.status,
                    "customer_name": "",
                    "customer_phone": "",
                    "created_by_email": sale.created_by.email if sale.created_by_id else "",
                    "gross_amount": gross_amount,
                    "refund_amount": refund_amount,
                    "net_amount": net_amount,
                    "summary": summary,
                }
            )
        return rows

    @classmethod
    def _ticket_rows(cls, *, club, utc_start, utc_end):
        ticket_sales = (
            GateTicketSale.objects.filter(
                club=club,
                created_at__gte=utc_start,
                created_at__lt=utc_end,
            )
            .select_related("created_by")
            .prefetch_related("tickets__ticket_type")
        )

        rows = []
        for sale in ticket_sales:
            gross_amount = cls._money(sale.total_amount)
            net_amount = gross_amount if sale.status == GateTicketSale.STATUS_ISSUED else Decimal("0.00")
            ticket_count = sale.tickets.count()
            summary = f"{ticket_count} ticket(s) for {sale.visit_date.isoformat()}"
            rows.append(
                {
                    "id": f"tickets-{sale.id}",
                    "source": "tickets",
                    "transaction_id": sale.id,
                    "reference": f"TICKET-{sale.id}",
                    "activity_at": sale.created_at,
                    "status": sale.status,
                    "customer_name": sale.buyer_name,
                    "customer_phone": sale.buyer_phone,
                    "created_by_email": sale.created_by.email if sale.created_by_id else "",
                    "gross_amount": gross_amount,
                    "refund_amount": Decimal("0.00"),
                    "net_amount": net_amount,
                    "summary": summary,
                }
            )
        return rows

    @classmethod
    def _event_rows(cls, *, club, utc_start, utc_end):
        reservations = (
            VenueReservation.objects.filter(club=club)
            .filter(
                Q(created_at__gte=utc_start, created_at__lt=utc_end)
                | Q(refunded_at__gte=utc_start, refunded_at__lt=utc_end)
            )
            .select_related("occasion_type", "created_by")
        )

        rows = []
        for reservation in reservations:
            is_refund_event = (
                reservation.refunded_at is not None
                and utc_start <= reservation.refunded_at < utc_end
            )
            activity_at = reservation.refunded_at if is_refund_event else reservation.created_at
            gross_amount = cls._money(reservation.paid_amount)
            refund_amount = cls._money(reservation.refunded_amount)
            net_amount = gross_amount - refund_amount

            if is_refund_event or reservation.payment_status == VenueReservation.PAYMENT_REFUNDED:
                status = "refunded"
            elif reservation.status == VenueReservation.STATUS_CANCELLED:
                status = "cancelled"
            else:
                status = reservation.payment_status

            summary = (
                f"{reservation.occasion_type.name} reservation · {reservation.guest_count} guest(s)"
            )
            rows.append(
                {
                    "id": f"events-{reservation.id}",
                    "source": "events",
                    "transaction_id": reservation.id,
                    "reference": f"EVENT-{reservation.id}",
                    "activity_at": activity_at,
                    "status": status,
                    "customer_name": reservation.guest_name,
                    "customer_phone": reservation.guest_phone,
                    "created_by_email": reservation.created_by.email if reservation.created_by_id else "",
                    "gross_amount": gross_amount,
                    "refund_amount": refund_amount,
                    "net_amount": net_amount,
                    "summary": summary,
                }
            )
        return rows

    @staticmethod
    def _apply_filters(rows, *, status_value="", search=""):
        filtered = rows
        if status_value:
            desired = status_value.strip().lower()
            filtered = [row for row in filtered if str(row.get("status", "")).lower() == desired]

        if search:
            needle = search.strip().lower()
            search_fields = (
                "reference",
                "source",
                "status",
                "customer_name",
                "customer_phone",
                "created_by_email",
                "summary",
            )
            filtered = [
                row
                for row in filtered
                if needle in " ".join(str(row.get(field, "")) for field in search_fields).lower()
            ]
        return filtered

    @staticmethod
    def _sort_rows(rows, *, ordering):
        reverse = ordering.startswith("-")
        field_name = ordering.lstrip("-")

        def sort_key(row):
            primary = row.get(field_name)
            return (primary, row.get("activity_at"), row.get("reference"))

        return sorted(rows, key=sort_key, reverse=reverse)

    @classmethod
    def list_transactions(
        cls,
        *,
        club,
        start_date,
        end_date,
        source="all",
        status="",
        search="",
        ordering="-activity_at",
    ):
        utc_start, utc_end = cls._get_utc_window(
            club=club,
            start_date=start_date,
            end_date=end_date,
        )

        rows = []
        if source in ("all", "products"):
            rows.extend(cls._product_rows(club=club, utc_start=utc_start, utc_end=utc_end))
        if source in ("all", "tickets"):
            rows.extend(cls._ticket_rows(club=club, utc_start=utc_start, utc_end=utc_end))
        if source in ("all", "events"):
            rows.extend(cls._event_rows(club=club, utc_start=utc_start, utc_end=utc_end))

        rows = cls._apply_filters(rows, status_value=status, search=search)
        return cls._sort_rows(rows, ordering=ordering)

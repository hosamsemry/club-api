from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework.exceptions import ValidationError

from core.services.audit_service import AuditService
from tickets.models import GateEntryDay, GateTicket, GateTicketSale, GateTicketType


class GateTicketService:
    @staticmethod
    def _club_today(club):
        tz = ZoneInfo(club.timezone or "UTC")
        return timezone.now().astimezone(tz).date()

    @staticmethod
    def _generate_code():
        while True:
            code = get_random_string(12).upper()
            if not GateTicket.objects.filter(code=code).exists():
                return code

    @staticmethod
    def _validate_ticket_type(*, club, ticket_type):
        if ticket_type.club_id != club.id:
            raise ValidationError({"ticket_type": "Ticket type does not exist."})
        if not ticket_type.is_active:
            raise ValidationError({"ticket_type": "Ticket type is inactive."})

    @staticmethod
    def _entry_day_for_sale(*, club, visit_date):
        entry_day = GateEntryDay.objects.select_for_update().filter(
            club=club,
            visit_date=visit_date,
        ).first()
        if entry_day is None:
            raise ValidationError({"visit_date": "No gate entry day configured for this date."})
        if not entry_day.is_open:
            raise ValidationError({"visit_date": "Gate entry is closed for this date."})
        return entry_day

    @staticmethod
    def _allocated_count(*, club, visit_date):
        return GateTicket.objects.filter(
            club=club,
            visit_date=visit_date,
        ).exclude(status=GateTicket.STATUS_VOIDED).count()

    @staticmethod
    def log_ticket_type_created(*, ticket_type, user):
        AuditService.log(
            action="gate_ticket_type_created",
            club=ticket_type.club,
            user=user,
            details={"ticket_type_id": ticket_type.id, "name": ticket_type.name},
        )

    @staticmethod
    def log_ticket_type_updated(*, ticket_type, user, deactivated=False):
        AuditService.log(
            action="gate_ticket_type_deactivated" if deactivated else "gate_ticket_type_updated",
            club=ticket_type.club,
            user=user,
            details={
                "ticket_type_id": ticket_type.id,
                "name": ticket_type.name,
                "price": str(ticket_type.price),
                "is_active": ticket_type.is_active,
            },
        )

    @staticmethod
    def log_entry_day_created(*, entry_day, user):
        AuditService.log(
            action="gate_entry_day_created",
            club=entry_day.club,
            user=user,
            details={
                "entry_day_id": entry_day.id,
                "visit_date": entry_day.visit_date.isoformat(),
                "daily_capacity": entry_day.daily_capacity,
                "is_open": entry_day.is_open,
            },
        )

    @staticmethod
    def log_entry_day_updated(*, entry_day, user):
        AuditService.log(
            action="gate_entry_day_updated",
            club=entry_day.club,
            user=user,
            details={
                "entry_day_id": entry_day.id,
                "visit_date": entry_day.visit_date.isoformat(),
                "daily_capacity": entry_day.daily_capacity,
                "is_open": entry_day.is_open,
            },
        )

    @staticmethod
    @transaction.atomic
    def create_sale(*, club, user, buyer_name, buyer_phone, visit_date, items, notes=""):
        entry_day = GateTicketService._entry_day_for_sale(club=club, visit_date=visit_date)
        total_quantity = 0
        total_amount = Decimal("0.00")

        for item in items:
            ticket_type = item["ticket_type"]
            quantity = item["quantity"]
            GateTicketService._validate_ticket_type(club=club, ticket_type=ticket_type)
            total_quantity += quantity
            total_amount += ticket_type.price * quantity

        allocated = GateTicketService._allocated_count(club=club, visit_date=visit_date)
        if allocated + total_quantity > entry_day.daily_capacity:
            raise ValidationError({"detail": "Daily gate capacity has been reached for this date."})

        sale = GateTicketSale.objects.create(
            club=club,
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            visit_date=visit_date,
            total_amount=total_amount,
            status=GateTicketSale.STATUS_ISSUED,
            created_by=user,
            notes=notes,
        )

        created_tickets = []
        for item in items:
            for _ in range(item["quantity"]):
                created_tickets.append(
                    GateTicket(
                        club=club,
                        sale=sale,
                        ticket_type=item["ticket_type"],
                        visit_date=visit_date,
                        code=GateTicketService._generate_code(),
                        status=GateTicket.STATUS_ISSUED,
                    )
                )
        GateTicket.objects.bulk_create(created_tickets)

        AuditService.log(
            action="gate_ticket_sale_created",
            club=club,
            user=user,
            details={
                "sale_id": sale.id,
                "buyer_name": buyer_name,
                "buyer_phone": buyer_phone,
                "visit_date": visit_date.isoformat(),
                "ticket_count": total_quantity,
                "total_amount": str(total_amount),
            },
        )
        return GateTicketSale.objects.select_related("club", "created_by").prefetch_related(
            "tickets__ticket_type"
        ).get(pk=sale.pk)

    @staticmethod
    @transaction.atomic
    def check_in_ticket(*, ticket, user):
        ticket = GateTicket.objects.select_for_update().select_related("club", "ticket_type", "sale").get(pk=ticket.pk)
        if ticket.status == GateTicket.STATUS_CHECKED_IN:
            raise ValidationError({"detail": "Ticket is already checked in."})
        if ticket.status == GateTicket.STATUS_VOIDED:
            raise ValidationError({"detail": "Voided tickets cannot be checked in."})
        if ticket.visit_date != GateTicketService._club_today(ticket.club):
            raise ValidationError({"detail": "Ticket is not valid for today."})

        ticket.status = GateTicket.STATUS_CHECKED_IN
        ticket.checked_in_at = timezone.now()
        ticket.checked_in_by = user
        ticket.save(update_fields=["status", "checked_in_at", "checked_in_by", "updated_at"])

        AuditService.log(
            action="gate_ticket_checked_in",
            club=ticket.club,
            user=user,
            details={
                "ticket_id": ticket.id,
                "sale_id": ticket.sale_id,
                "ticket_type": ticket.ticket_type.name,
                "code": ticket.code,
                "visit_date": ticket.visit_date.isoformat(),
            },
        )
        return ticket

    @staticmethod
    def check_in_ticket_by_code(*, club, user, code):
        ticket = GateTicket.objects.filter(club=club, code=code).first()
        if ticket is None:
            raise ValidationError({"code": "Ticket code was not found."})
        return GateTicketService.check_in_ticket(ticket=ticket, user=user)

    @staticmethod
    @transaction.atomic
    def void_ticket(*, ticket, user, note=""):
        ticket = GateTicket.objects.select_for_update().select_related("sale", "ticket_type", "club").get(pk=ticket.pk)
        if ticket.status == GateTicket.STATUS_CHECKED_IN:
            raise ValidationError({"detail": "Checked-in tickets cannot be voided."})
        if ticket.status == GateTicket.STATUS_VOIDED:
            raise ValidationError({"detail": "Ticket is already voided."})

        ticket.status = GateTicket.STATUS_VOIDED
        ticket.save(update_fields=["status", "updated_at"])

        remaining_active = ticket.sale.tickets.exclude(status=GateTicket.STATUS_VOIDED).exists()
        if not remaining_active:
            ticket.sale.status = GateTicketSale.STATUS_VOIDED
            ticket.sale.save(update_fields=["status", "updated_at"])

        AuditService.log(
            action="gate_ticket_voided",
            club=ticket.club,
            user=user,
            details={
                "ticket_id": ticket.id,
                "sale_id": ticket.sale_id,
                "ticket_type": ticket.ticket_type.name,
                "code": ticket.code,
                "note": note,
            },
        )
        return ticket

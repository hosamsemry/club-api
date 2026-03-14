from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from core.services.audit_service import AuditService
from events.models import VenueReservation


class ReservationService:
    @staticmethod
    def _derive_payment_status(*, status, total_amount, paid_amount):
        if status == VenueReservation.STATUS_CANCELLED and paid_amount == Decimal("0.00"):
            return VenueReservation.PAYMENT_REFUNDED
        if paid_amount == Decimal("0.00"):
            return VenueReservation.PAYMENT_UNPAID
        if paid_amount < total_amount:
            return VenueReservation.PAYMENT_PARTIAL
        return VenueReservation.PAYMENT_PAID

    @staticmethod
    def _validate_occasion_type(*, club, occasion_type):
        if occasion_type.club_id != club.id:
            raise ValidationError({"occasion_type": "Occasion type does not exist."})
        if not occasion_type.is_active:
            raise ValidationError({"occasion_type": "Occasion type is inactive."})

    @staticmethod
    def _validate_time_range(*, starts_at, ends_at):
        if starts_at >= ends_at:
            raise ValidationError({"ends_at": "End time must be after start time."})

    @staticmethod
    def _validate_guest_count(*, guest_count):
        if guest_count <= 0:
            raise ValidationError({"guest_count": "Guest count must be greater than zero."})

    @staticmethod
    def _validate_amounts(*, total_amount, paid_amount):
        if total_amount < Decimal("0.00"):
            raise ValidationError({"total_amount": "Total amount cannot be negative."})
        if paid_amount < Decimal("0.00"):
            raise ValidationError({"paid_amount": "Paid amount cannot be negative."})
        if paid_amount > total_amount:
            raise ValidationError({"paid_amount": "Paid amount cannot exceed total amount."})

    @staticmethod
    def _overlap_queryset(*, club, starts_at, ends_at, exclude_id=None):
        queryset = VenueReservation.objects.select_for_update().filter(
            club=club,
        ).exclude(status=VenueReservation.STATUS_CANCELLED)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.filter(
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )

    @staticmethod
    def _ensure_no_overlap(*, club, starts_at, ends_at, exclude_id=None):
        conflict_exists = ReservationService._overlap_queryset(
            club=club,
            starts_at=starts_at,
            ends_at=ends_at,
            exclude_id=exclude_id,
        ).exists()
        if conflict_exists:
            raise ValidationError({"detail": "This booking overlaps an existing reservation."})

    @staticmethod
    def log_occasion_type_created(*, occasion_type, user):
        AuditService.log(
            action="occasion_type_created",
            club=occasion_type.club,
            user=user,
            details={"occasion_type_id": occasion_type.id, "name": occasion_type.name},
        )

    @staticmethod
    def log_occasion_type_updated(*, occasion_type, user, deactivated=False):
        AuditService.log(
            action="occasion_type_deactivated" if deactivated else "occasion_type_updated",
            club=occasion_type.club,
            user=user,
            details={
                "occasion_type_id": occasion_type.id,
                "name": occasion_type.name,
                "is_active": occasion_type.is_active,
            },
        )

    @staticmethod
    @transaction.atomic
    def create_reservation(
        *,
        club,
        user,
        occasion_type,
        guest_name,
        guest_phone,
        starts_at,
        ends_at,
        guest_count,
        total_amount,
        paid_amount=Decimal("0.00"),
        notes="",
    ):
        ReservationService._validate_occasion_type(club=club, occasion_type=occasion_type)
        ReservationService._validate_time_range(starts_at=starts_at, ends_at=ends_at)
        ReservationService._validate_guest_count(guest_count=guest_count)
        ReservationService._validate_amounts(
            total_amount=Decimal(total_amount),
            paid_amount=Decimal(paid_amount),
        )
        ReservationService._ensure_no_overlap(club=club, starts_at=starts_at, ends_at=ends_at)

        status = (
            VenueReservation.STATUS_CONFIRMED
            if Decimal(paid_amount) == Decimal(total_amount) and Decimal(total_amount) > Decimal("0.00")
            else VenueReservation.STATUS_PENDING
        )
        reservation = VenueReservation.objects.create(
            club=club,
            occasion_type=occasion_type,
            guest_name=guest_name,
            guest_phone=guest_phone,
            starts_at=starts_at,
            ends_at=ends_at,
            guest_count=guest_count,
            total_amount=Decimal(total_amount),
            paid_amount=Decimal(paid_amount),
            status=status,
            payment_status=ReservationService._derive_payment_status(
                status=status,
                total_amount=Decimal(total_amount),
                paid_amount=Decimal(paid_amount),
            ),
            created_by=user,
            notes=notes,
        )

        AuditService.log(
            action="reservation_created",
            club=club,
            user=user,
            details={
                "reservation_id": reservation.id,
                "occasion_type": occasion_type.name,
                "guest_name": guest_name,
                "guest_phone": guest_phone,
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "guest_count": guest_count,
                "total_amount": str(reservation.total_amount),
                "paid_amount": str(reservation.paid_amount),
            },
        )

        return reservation

    @staticmethod
    @transaction.atomic
    def update_reservation(
        *,
        reservation,
        user,
        occasion_type,
        guest_name,
        guest_phone,
        starts_at,
        ends_at,
        guest_count,
        total_amount,
        paid_amount,
        notes="",
    ):
        reservation = VenueReservation.objects.select_for_update().get(pk=reservation.pk)
        if reservation.status == VenueReservation.STATUS_CANCELLED:
            raise ValidationError({"detail": "Cancelled reservations cannot be edited."})

        ReservationService._validate_occasion_type(club=reservation.club, occasion_type=occasion_type)
        ReservationService._validate_time_range(starts_at=starts_at, ends_at=ends_at)
        ReservationService._validate_guest_count(guest_count=guest_count)
        ReservationService._validate_amounts(
            total_amount=Decimal(total_amount),
            paid_amount=Decimal(paid_amount),
        )
        ReservationService._ensure_no_overlap(
            club=reservation.club,
            starts_at=starts_at,
            ends_at=ends_at,
            exclude_id=reservation.id,
        )

        reservation.occasion_type = occasion_type
        reservation.guest_name = guest_name
        reservation.guest_phone = guest_phone
        reservation.starts_at = starts_at
        reservation.ends_at = ends_at
        reservation.guest_count = guest_count
        reservation.total_amount = Decimal(total_amount)
        reservation.paid_amount = Decimal(paid_amount)
        reservation.notes = notes
        if reservation.status != VenueReservation.STATUS_CANCELLED:
            reservation.status = (
                VenueReservation.STATUS_CONFIRMED
                if reservation.paid_amount == reservation.total_amount and reservation.total_amount > Decimal("0.00")
                else VenueReservation.STATUS_PENDING
            )
        reservation.payment_status = ReservationService._derive_payment_status(
            status=reservation.status,
            total_amount=reservation.total_amount,
            paid_amount=reservation.paid_amount,
        )
        reservation.save()
        return reservation

    @staticmethod
    @transaction.atomic
    def record_payment(*, reservation, user, amount, note=""):
        reservation = VenueReservation.objects.select_for_update().get(pk=reservation.pk)
        if reservation.status == VenueReservation.STATUS_CANCELLED:
            raise ValidationError({"detail": "Cancelled reservations cannot receive payments."})

        amount = Decimal(amount)
        if amount <= Decimal("0.00"):
            raise ValidationError({"amount": "Payment amount must be greater than zero."})

        if reservation.paid_amount + amount > reservation.total_amount:
            raise ValidationError({"amount": "Payment exceeds the reservation total."})

        reservation.paid_amount += amount
        if reservation.paid_amount == reservation.total_amount and reservation.total_amount > Decimal("0.00"):
            reservation.status = VenueReservation.STATUS_CONFIRMED
        reservation.payment_status = ReservationService._derive_payment_status(
            status=reservation.status,
            total_amount=reservation.total_amount,
            paid_amount=reservation.paid_amount,
        )
        reservation.save(update_fields=["paid_amount", "status", "payment_status", "updated_at"])

        AuditService.log(
            action="reservation_payment_recorded",
            club=reservation.club,
            user=user,
            details={
                "reservation_id": reservation.id,
                "amount": str(amount),
                "paid_amount": str(reservation.paid_amount),
                "payment_status": reservation.payment_status,
                "note": note,
            },
        )
        return reservation

    @staticmethod
    @transaction.atomic
    def cancel_reservation(*, reservation, user, refund_amount=None, note=""):
        reservation = VenueReservation.objects.select_for_update().get(pk=reservation.pk)
        if reservation.status == VenueReservation.STATUS_CANCELLED:
            raise ValidationError({"detail": "Reservation is already cancelled."})

        refund_amount = Decimal(refund_amount or "0.00")
        if refund_amount < Decimal("0.00"):
            raise ValidationError({"refund_amount": "Refund amount cannot be negative."})
        if refund_amount > reservation.paid_amount:
            raise ValidationError({"refund_amount": "Refund amount cannot exceed paid amount."})

        reservation.status = VenueReservation.STATUS_CANCELLED
        reservation.cancelled_at = timezone.now()
        if refund_amount > Decimal("0.00"):
            reservation.paid_amount -= refund_amount
            reservation.refunded_amount += refund_amount
            reservation.refunded_at = timezone.now()
        reservation.payment_status = ReservationService._derive_payment_status(
            status=reservation.status,
            total_amount=reservation.total_amount,
            paid_amount=reservation.paid_amount,
        )
        reservation.save()

        AuditService.log(
            action="reservation_cancelled",
            club=reservation.club,
            user=user,
            details={
                "reservation_id": reservation.id,
                "refund_amount": str(refund_amount),
                "paid_amount": str(reservation.paid_amount),
                "note": note,
            },
        )
        if refund_amount > Decimal("0.00"):
            AuditService.log(
                action="reservation_refunded",
                club=reservation.club,
                user=user,
                details={
                    "reservation_id": reservation.id,
                    "refund_amount": str(refund_amount),
                    "refunded_amount_total": str(reservation.refunded_amount),
                    "note": note,
                },
            )
        return reservation

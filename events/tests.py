from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from clubs.models import Club
from core.models import AuditLog
from events.models import OccasionType, VenueReservation


User = get_user_model()


class VenueReservationTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Club One")
        self.other_club = Club.objects.create(name="Club Two")
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
        self.occasion_type = OccasionType.objects.create(club=self.club, name="Wedding")
        self.other_type = OccasionType.objects.create(club=self.other_club, name="Birthday")
        self.starts_at = timezone.now() + timedelta(days=5)
        self.ends_at = self.starts_at + timedelta(hours=6)

    def test_owner_can_create_occasion_type(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("occasiontype-list"),
            {"name": "Engagement", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(OccasionType.objects.filter(club=self.club, name="Engagement").exists())

    def test_cashier_cannot_manage_occasion_types(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.post(
            reverse("occasiontype-list"),
            {"name": "Private Party"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_reservation(self):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse("venuereservation-list"),
            {
                "occasion_type": self.occasion_type.id,
                "guest_name": "Sara Ahmed",
                "guest_phone": "01000000000",
                "starts_at": self.starts_at.isoformat(),
                "ends_at": self.ends_at.isoformat(),
                "guest_count": 120,
                "total_amount": "5000.00",
                "paid_amount": "1000.00",
                "notes": "Family booking",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reservation = VenueReservation.objects.get(club=self.club, guest_phone="01000000000")
        self.assertEqual(reservation.payment_status, VenueReservation.PAYMENT_PARTIAL)
        self.assertTrue(AuditLog.objects.filter(action="reservation_created").exists())

    def test_overlapping_reservation_is_rejected(self):
        VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Existing",
            guest_phone="01111111111",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=50,
            total_amount=Decimal("2000.00"),
            paid_amount=Decimal("0.00"),
            status=VenueReservation.STATUS_CONFIRMED,
            payment_status=VenueReservation.PAYMENT_UNPAID,
            created_by=self.owner,
        )
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("venuereservation-list"),
            {
                "occasion_type": self.occasion_type.id,
                "guest_name": "Overlap",
                "guest_phone": "01222222222",
                "starts_at": (self.starts_at + timedelta(hours=1)).isoformat(),
                "ends_at": (self.ends_at + timedelta(hours=1)).isoformat(),
                "guest_count": 40,
                "total_amount": "3000.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_reservation_no_longer_blocks_new_booking(self):
        reservation = VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Cancelled",
            guest_phone="01333333333",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=50,
            total_amount=Decimal("2000.00"),
            paid_amount=Decimal("500.00"),
            refunded_amount=Decimal("500.00"),
            status=VenueReservation.STATUS_CANCELLED,
            payment_status=VenueReservation.PAYMENT_REFUNDED,
            cancelled_at=timezone.now(),
            refunded_at=timezone.now(),
            created_by=self.owner,
        )
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("venuereservation-list"),
            {
                "occasion_type": self.occasion_type.id,
                "guest_name": "New Booking",
                "guest_phone": "01444444444",
                "starts_at": reservation.starts_at.isoformat(),
                "ends_at": reservation.ends_at.isoformat(),
                "guest_count": 70,
                "total_amount": "3500.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_time_range_is_rejected(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("venuereservation-list"),
            {
                "occasion_type": self.occasion_type.id,
                "guest_name": "Bad Times",
                "guest_phone": "01555555555",
                "starts_at": self.ends_at.isoformat(),
                "ends_at": self.starts_at.isoformat(),
                "guest_count": 10,
                "total_amount": "1000.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_record_payment_transitions_to_paid(self):
        reservation = VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Partial",
            guest_phone="01666666666",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=80,
            total_amount=Decimal("3000.00"),
            paid_amount=Decimal("1000.00"),
            status=VenueReservation.STATUS_CONFIRMED,
            payment_status=VenueReservation.PAYMENT_PARTIAL,
            created_by=self.owner,
        )
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("venuereservation-record-payment", args=[reservation.id]),
            {"amount": "2000.00", "note": "Final payment"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.payment_status, VenueReservation.PAYMENT_PAID)
        self.assertEqual(reservation.paid_amount, Decimal("3000.00"))

    def test_overpayment_is_rejected(self):
        reservation = VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Overpay",
            guest_phone="01777777777",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=30,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("900.00"),
            status=VenueReservation.STATUS_PENDING,
            payment_status=VenueReservation.PAYMENT_PARTIAL,
            created_by=self.owner,
        )
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("venuereservation-record-payment", args=[reservation.id]),
            {"amount": "200.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_with_full_refund_marks_refunded(self):
        reservation = VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Refunded",
            guest_phone="01888888888",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=50,
            total_amount=Decimal("2500.00"),
            paid_amount=Decimal("2500.00"),
            status=VenueReservation.STATUS_CONFIRMED,
            payment_status=VenueReservation.PAYMENT_PAID,
            created_by=self.owner,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse("venuereservation-cancel", args=[reservation.id]),
            {"refund_amount": "2500.00", "note": "Customer cancelled"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, VenueReservation.STATUS_CANCELLED)
        self.assertEqual(reservation.payment_status, VenueReservation.PAYMENT_REFUNDED)
        self.assertTrue(AuditLog.objects.filter(action="reservation_refunded").exists())

    def test_list_is_scoped_to_current_club(self):
        VenueReservation.objects.create(
            club=self.club,
            occasion_type=self.occasion_type,
            guest_name="Visible",
            guest_phone="01999999999",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=20,
            total_amount=Decimal("1200.00"),
            paid_amount=Decimal("0.00"),
            status=VenueReservation.STATUS_PENDING,
            payment_status=VenueReservation.PAYMENT_UNPAID,
            created_by=self.owner,
        )
        other_owner = User.objects.create_user(
            email="owner2@club.com",
            username="owner2",
            password="secret123",
            club=self.other_club,
            role="owner",
        )
        VenueReservation.objects.create(
            club=self.other_club,
            occasion_type=self.other_type,
            guest_name="Hidden",
            guest_phone="02000000000",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            guest_count=40,
            total_amount=Decimal("2200.00"),
            paid_amount=Decimal("0.00"),
            status=VenueReservation.STATUS_PENDING,
            payment_status=VenueReservation.PAYMENT_UNPAID,
            created_by=other_owner,
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("venuereservation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_cashier_cannot_manage_reservations(self):
        self.client.force_authenticate(self.cashier)
        response = self.client.get(reverse("venuereservation-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

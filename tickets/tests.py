from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from clubs.models import Club
from core.models import AuditLog
from tickets.models import GateEntryDay, GateTicket, GateTicketSale, GateTicketType


User = get_user_model()


class GateTicketTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Main Club", timezone="UTC")
        self.other_club = Club.objects.create(name="Other Club", timezone="UTC")
        self.owner = User.objects.create_user(
            email="owner@tickets.com",
            username="owner_tickets",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="manager@tickets.com",
            username="manager_tickets",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="cashier@tickets.com",
            username="cashier_tickets",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.other_owner = User.objects.create_user(
            email="other@tickets.com",
            username="other_tickets",
            password="secret123",
            club=self.other_club,
            role="owner",
        )
        self.visit_date = timezone.localdate() + timedelta(days=1)
        self.entry_day = GateEntryDay.objects.create(
            club=self.club,
            visit_date=self.visit_date,
            daily_capacity=5,
            is_open=True,
        )
        self.ticket_type = GateTicketType.objects.create(
            club=self.club,
            name="Adult",
            price=Decimal("100.00"),
            is_active=True,
            display_order=1,
        )
        self.other_ticket_type = GateTicketType.objects.create(
            club=self.other_club,
            name="VIP",
            price=Decimal("200.00"),
            is_active=True,
            display_order=1,
        )

    def test_owner_can_create_ticket_type(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("gatetickettype-list"),
            {"name": "Child", "price": "50.00", "is_active": True, "display_order": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GateTicketType.objects.filter(club=self.club, name="Child").exists())

    def test_cashier_cannot_manage_ticket_types(self):
        self.client.force_authenticate(self.cashier)
        response = self.client.post(
            reverse("gatetickettype-list"),
            {"name": "Child", "price": "50.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_entry_day(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            reverse("gateentryday-list"),
            {
                "visit_date": (self.visit_date + timedelta(days=1)).isoformat(),
                "daily_capacity": 10,
                "is_open": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            GateEntryDay.objects.filter(club=self.club, visit_date=self.visit_date + timedelta(days=1)).exists()
        )

    def test_cashier_can_create_sale_and_tickets(self):
        self.client.force_authenticate(self.cashier)
        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Sara Ahmed",
                "buyer_phone": "01000000000",
                "visit_date": self.visit_date.isoformat(),
                "notes": "Family group",
                "items": [
                    {"ticket_type": self.ticket_type.id, "quantity": 2},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sale = GateTicketSale.objects.get(club=self.club, buyer_phone="01000000000")
        self.assertEqual(sale.total_amount, Decimal("200.00"))
        self.assertEqual(sale.tickets.count(), 2)
        self.assertTrue(AuditLog.objects.filter(action="gate_ticket_sale_created").exists())

    def test_inactive_ticket_type_is_rejected(self):
        self.ticket_type.is_active = False
        self.ticket_type.save(update_fields=["is_active"])
        self.client.force_authenticate(self.cashier)

        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Mohamed",
                "buyer_phone": "01111111111",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_foreign_club_ticket_type_is_rejected(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Mohamed",
                "buyer_phone": "01111111111",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.other_ticket_type.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_or_missing_entry_day_is_rejected(self):
        self.entry_day.is_open = False
        self.entry_day.save(update_fields=["is_open"])
        self.client.force_authenticate(self.cashier)

        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Mohamed",
                "buyer_phone": "01111111111",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_capacity_blocks_over_issue(self):
        self.client.force_authenticate(self.cashier)
        GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Existing",
            buyer_phone="01200000000",
            visit_date=self.visit_date,
            total_amount=Decimal("400.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.cashier,
        )
        sale = GateTicketSale.objects.get(buyer_phone="01200000000")
        for idx in range(4):
            GateTicket.objects.create(
                club=self.club,
                sale=sale,
                ticket_type=self.ticket_type,
                visit_date=self.visit_date,
                code=f"CODE-{idx}",
                status=GateTicket.STATUS_ISSUED,
            )

        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Mohamed",
                "buyer_phone": "01111111111",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 2}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_voided_ticket_releases_capacity(self):
        self.client.force_authenticate(self.cashier)
        sale_response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Buyer",
                "buyer_phone": "01300000000",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 5}],
            },
            format="json",
        )
        sale_id = sale_response.data["id"]
        ticket_id = sale_response.data["tickets"][0]["id"]
        void_response = self.client.post(
            reverse("gateticket-void", args=[ticket_id]),
            {"note": "Customer left"},
            format="json",
        )
        self.assertEqual(void_response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "New Buyer",
                "buyer_phone": "01400000000",
                "visit_date": self.visit_date.isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_ticket_can_check_in_once(self):
        self.client.force_authenticate(self.cashier)
        sale_response = self.client.post(
            reverse("gateticketsale-list"),
            {
                "buyer_name": "Check In",
                "buyer_phone": "01500000000",
                "visit_date": timezone.localdate().isoformat(),
                "items": [{"ticket_type": self.ticket_type.id, "quantity": 1}],
            },
            format="json",
        )
        if sale_response.status_code != status.HTTP_201_CREATED:
            GateEntryDay.objects.update_or_create(
                club=self.club,
                visit_date=timezone.localdate(),
                defaults={"daily_capacity": 5, "is_open": True},
            )
            sale_response = self.client.post(
                reverse("gateticketsale-list"),
                {
                    "buyer_name": "Check In",
                    "buyer_phone": "01500000000",
                    "visit_date": timezone.localdate().isoformat(),
                    "items": [{"ticket_type": self.ticket_type.id, "quantity": 1}],
                },
                format="json",
            )
        ticket_id = sale_response.data["tickets"][0]["id"]

        first = self.client.post(reverse("gateticket-check-in", args=[ticket_id]), {}, format="json")
        second = self.client.post(reverse("gateticket-check-in", args=[ticket_id]), {}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_date_check_in_fails(self):
        sale = GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Wrong Date",
            buyer_phone="01600000000",
            visit_date=self.visit_date,
            total_amount=Decimal("100.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.cashier,
        )
        ticket = GateTicket.objects.create(
            club=self.club,
            sale=sale,
            ticket_type=self.ticket_type,
            visit_date=self.visit_date,
            code="WRONG-DATE",
            status=GateTicket.STATUS_ISSUED,
        )
        self.client.force_authenticate(self.cashier)

        response = self.client.post(reverse("gateticket-check-in", args=[ticket.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_voided_ticket_cannot_check_in(self):
        sale = GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Voided",
            buyer_phone="01700000000",
            visit_date=timezone.localdate(),
            total_amount=Decimal("100.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.cashier,
        )
        ticket = GateTicket.objects.create(
            club=self.club,
            sale=sale,
            ticket_type=self.ticket_type,
            visit_date=timezone.localdate(),
            code="VOIDED",
            status=GateTicket.STATUS_VOIDED,
        )
        self.client.force_authenticate(self.cashier)

        response = self.client.post(reverse("gateticket-check-in", args=[ticket.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_void_all_tickets_marks_sale_voided(self):
        sale = GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Void Sale",
            buyer_phone="01800000000",
            visit_date=self.visit_date,
            total_amount=Decimal("200.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.cashier,
        )
        ticket_one = GateTicket.objects.create(
            club=self.club,
            sale=sale,
            ticket_type=self.ticket_type,
            visit_date=self.visit_date,
            code="VOID-1",
            status=GateTicket.STATUS_ISSUED,
        )
        ticket_two = GateTicket.objects.create(
            club=self.club,
            sale=sale,
            ticket_type=self.ticket_type,
            visit_date=self.visit_date,
            code="VOID-2",
            status=GateTicket.STATUS_ISSUED,
        )
        self.client.force_authenticate(self.cashier)

        self.client.post(reverse("gateticket-void", args=[ticket_one.id]), {}, format="json")
        response = self.client.post(reverse("gateticket-void", args=[ticket_two.id]), {}, format="json")

        sale.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sale.status, GateTicketSale.STATUS_VOIDED)

    def test_list_is_scoped_to_current_club(self):
        self.client.force_authenticate(self.owner)
        GateTicketSale.objects.create(
            club=self.club,
            buyer_name="Visible",
            buyer_phone="01900000000",
            visit_date=self.visit_date,
            total_amount=Decimal("100.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.owner,
        )
        GateTicketSale.objects.create(
            club=self.other_club,
            buyer_name="Hidden",
            buyer_phone="02000000000",
            visit_date=self.visit_date,
            total_amount=Decimal("100.00"),
            status=GateTicketSale.STATUS_ISSUED,
            created_by=self.other_owner,
        )

        response = self.client.get(reverse("gateticketsale-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

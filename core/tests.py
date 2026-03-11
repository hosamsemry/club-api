from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from clubs.models import Club
from core.models import AuditLog


User = get_user_model()


class AuditLogViewSetTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="Main Club")
        self.other_club = Club.objects.create(name="Other Club")

        self.owner = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="secret123",
            club=self.club,
            role="owner",
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            username="manager",
            password="secret123",
            club=self.club,
            role="manager",
        )
        self.cashier = User.objects.create_user(
            email="cashier@example.com",
            username="cashier",
            password="secret123",
            club=self.club,
            role="cashier",
        )
        self.other_owner = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="secret123",
            club=self.other_club,
            role="owner",
        )

        self.audit_log = AuditLog.objects.create(
            action="sale_created",
            club=self.club,
            user=self.owner,
            details={"sale_id": 1},
            method="POST",
            path="/api/sales/",
            status_code=201,
        )
        AuditLog.objects.create(
            action="sale_refunded",
            club=self.other_club,
            user=self.other_owner,
            details={"sale_id": 2},
        )

    def test_owner_can_list_only_club_audit_logs(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("auditlog-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.audit_log.id)

    def test_manager_can_retrieve_audit_log(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(reverse("auditlog-detail", args=[self.audit_log.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "sale_created")

    def test_cashier_cannot_access_audit_logs(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.get(reverse("auditlog-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

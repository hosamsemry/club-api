from django.contrib.auth import get_user_model
from django.test import TestCase

from clubs.models import Club


User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_requires_club_and_role(self):
        with self.assertRaisesMessage(ValueError, "Non-superusers must belong to a club."):
            User.objects.create_user(
                email="user@example.com",
                username="user",
                password="secret123",
                role="owner",
            )

        club = Club.objects.create(name="Test Club")
        with self.assertRaisesMessage(ValueError, "Non-superusers must have a role."):
            User.objects.create_user(
                email="user2@example.com",
                username="user2",
                password="secret123",
                club=club,
            )

    def test_create_superuser_without_club(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="secret123",
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertIsNone(user.club)
        self.assertEqual(user.role, "")

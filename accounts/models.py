from django.db import models
from clubs.models import Club
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("cashier", "Cashier"),
        ("staff", "Staff"),
    ]
    email = models.EmailField(unique=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="users")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.email} - {self.club.name}"
    

#  Owner

# Full control
# Can manage subscription
# Can manage users

# Manager

# Can manage inventory
# Can see reports
# Cannot manage subscription

# Cashier

# Can create sales
# Cannot edit products
# Staff
# Limited (future use)   
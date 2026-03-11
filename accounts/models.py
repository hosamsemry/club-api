from django.db import models
from clubs.models import Club
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        if not extra_fields.get("club"):
            raise ValueError("Non-superusers must belong to a club.")
        if not extra_fields.get("role"):
            raise ValueError("Non-superusers must have a role.")

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "")
        extra_fields.setdefault("club", None)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("cashier", "Cashier"),
        ("staff", "Staff"),
    ]
    email = models.EmailField(unique=True)
    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="users", null=True, blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, default="")
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        club_name = self.club.name if self.club_id else "No club"
        return f"{self.email} - {club_name}"
    

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

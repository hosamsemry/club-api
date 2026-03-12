from time import timezone
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class Club(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default="UTC")
    subscription_plan = models.ForeignKey(
        "SubscriptionPlan", on_delete=models.SET_NULL, null=True, blank=True
    )
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            while Club.all_objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{get_random_string(4)}"
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["subscription_end"]),
            models.Index(fields=["is_active"]),
        ]


class SubscriptionPlan(BaseModel):
    PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    features = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class TenantBaseModel(BaseModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)ss")

    class Meta:
        abstract = True

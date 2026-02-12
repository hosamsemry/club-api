from django.db import models


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
    subscription_plan = models.ForeignKey('SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self): return self.name


class SubscriptionPlan(BaseModel):
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    features = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class TenantBaseModel(BaseModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='%(class)ss')

    class Meta:
        abstract = True
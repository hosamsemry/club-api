from django.contrib import admin
from .models import Club, SubscriptionPlan

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "timezone", "subscription_plan", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "subscription_plan")

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "period", "created_at")
    search_fields = ("name",)
    list_filter = ("period",)
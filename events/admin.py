from django.contrib import admin
from events.models import OccasionType, VenueReservation


@admin.register(OccasionType)
class OccasionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "is_active")
    list_filter = ("club", "is_active")
    search_fields = ("name",)


@admin.register(VenueReservation)
class VenueReservationAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name",
        "occasion_type",
        "club",
        "starts_at",
        "status",
        "payment_status",
    )
    list_filter = ("club", "status", "payment_status", "occasion_type")
    search_fields = ("guest_name", "guest_phone", "notes")

from django.contrib import admin
from tickets.models import GateEntryDay, GateTicket, GateTicketSale, GateTicketType


@admin.register(GateTicketType)
class GateTicketTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "price", "is_active", "display_order")
    list_filter = ("club", "is_active")
    search_fields = ("name",)


@admin.register(GateEntryDay)
class GateEntryDayAdmin(admin.ModelAdmin):
    list_display = ("club", "visit_date", "daily_capacity", "is_open")
    list_filter = ("club", "is_open")
    search_fields = ("visit_date",)


@admin.register(GateTicketSale)
class GateTicketSaleAdmin(admin.ModelAdmin):
    list_display = ("buyer_name", "club", "visit_date", "total_amount", "status", "created_by")
    list_filter = ("club", "visit_date", "status")
    search_fields = ("buyer_name", "buyer_phone", "notes")


@admin.register(GateTicket)
class GateTicketAdmin(admin.ModelAdmin):
    list_display = ("code", "ticket_type", "club", "visit_date", "status", "checked_in_by")
    list_filter = ("club", "visit_date", "status", "ticket_type")
    search_fields = ("code", "sale__buyer_name", "sale__buyer_phone")

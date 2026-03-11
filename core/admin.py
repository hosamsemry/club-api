from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "club", "created_at")
    list_filter = ("action", "club")
    search_fields = ("user__username", "details")
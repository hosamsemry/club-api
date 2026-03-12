from django.contrib import admin
from reporting.models import DailyClubReport


@admin.register(DailyClubReport)
class DailyClubReportAdmin(admin.ModelAdmin):
    list_display = ("club", "report_date", "sales_count", "total_revenue", "generated_at")
    list_filter = ("club", "report_date", "timezone")
    search_fields = ("club__name",)

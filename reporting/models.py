from django.db import models

from clubs.models import BaseModel, Club


class DailyClubReport(BaseModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="daily_reports")
    report_date = models.DateField()
    timezone = models.CharField(max_length=64)
    source_window_start = models.DateTimeField()
    source_window_end = models.DateTimeField()
    sales_count = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    audit_action_counts = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club", "report_date"], name="unique_daily_report_per_club_date"
            )
        ]
        indexes = [
            models.Index(fields=["club", "report_date"]),
            models.Index(fields=["report_date"]),
        ]

    def __str__(self):
        return f"{self.club.name} - {self.report_date}"

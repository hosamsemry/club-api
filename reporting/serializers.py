from rest_framework import serializers

from reporting.models import DailyClubReport


class DailyClubReportSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    csv_file_url = serializers.SerializerMethodField()

    class Meta:
        model = DailyClubReport
        fields = [
            "id",
            "club",
            "club_name",
            "report_date",
            "timezone",
            "source_window_start",
            "source_window_end",
            "sales_count",
            "total_revenue",
            "audit_action_counts",
            "generated_at",
            "csv_file_url",
        ]

    def get_csv_file_url(self, obj):
        request = self.context.get("request")
        if not obj.csv_file:
            return None
        url = obj.csv_file.url
        if request is None:
            return url
        return request.build_absolute_uri(url)

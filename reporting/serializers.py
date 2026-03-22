from rest_framework import serializers

from reporting.models import DailyClubReport


REVENUE_FIELD_CHOICES = ("tickets", "products", "events")


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


class RevenueQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    fields = serializers.ListField(
        child=serializers.ChoiceField(choices=REVENUE_FIELD_CHOICES),
        min_length=1,
    )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        seen = set()
        unique_fields = []
        for f in attrs["fields"]:
            if f not in seen:
                seen.add(f)
                unique_fields.append(f)
        attrs["fields"] = unique_fields
        return attrs


class RevenueResponseSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    tickets = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    products = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    events = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)

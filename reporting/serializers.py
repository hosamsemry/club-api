from rest_framework import serializers

from reporting.models import DailyClubReport


REVENUE_FIELD_CHOICES = ("tickets", "products", "events")
TRANSACTION_SOURCE_CHOICES = REVENUE_FIELD_CHOICES


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
            "revenue_breakdown",
            "activity_summary",
            "top_products",
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


class TransactionsQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    source = serializers.ChoiceField(
        choices=(("all", "All"),) + tuple((choice, choice.title()) for choice in TRANSACTION_SOURCE_CHOICES),
        required=False,
        default="all",
    )
    status = serializers.CharField(required=False, allow_blank=True)
    search = serializers.CharField(required=False, allow_blank=True)
    ordering = serializers.ChoiceField(
        choices=("-activity_at", "activity_at", "-net_amount", "net_amount"),
        required=False,
        default="-activity_at",
    )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs


class TransactionRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    source = serializers.ChoiceField(choices=TRANSACTION_SOURCE_CHOICES)
    transaction_id = serializers.IntegerField()
    reference = serializers.CharField()
    activity_at = serializers.DateTimeField()
    status = serializers.CharField()
    customer_name = serializers.CharField(allow_blank=True)
    customer_phone = serializers.CharField(allow_blank=True)
    created_by_email = serializers.CharField(allow_blank=True)
    gross_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    refund_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    summary = serializers.CharField()


class RevenueResponseSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    tickets = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    products = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    events = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)

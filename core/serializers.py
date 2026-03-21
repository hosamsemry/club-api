from rest_framework import serializers

from core.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "user",
            "user_email",
            "club",
            "club_name",
            "details",
            "path",
            "method",
            "status_code",
            "ip_address",
            "created_at",
        ]


class DashboardRecentActivitySerializer(serializers.Serializer):
    action = serializers.CharField()
    user_email = serializers.EmailField(allow_null=True)
    created_at = serializers.DateTimeField()


class DashboardSummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    low_stock_alert_count = serializers.IntegerField()
    today_reservations_count = serializers.IntegerField()
    pending_reservations_count = serializers.IntegerField()
    today_ticket_sales_count = serializers.IntegerField()
    today_ticket_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_checked_in_tickets_count = serializers.IntegerField()
    recent_activity = DashboardRecentActivitySerializer(many=True)

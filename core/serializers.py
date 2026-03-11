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

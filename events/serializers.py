from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from events.models import OccasionType, VenueReservation


class OccasionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccasionType
        fields = ["id", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class VenueReservationReadSerializer(serializers.ModelSerializer):
    occasion_type_name = serializers.CharField(source="occasion_type.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = VenueReservation
        fields = [
            "id",
            "occasion_type",
            "occasion_type_name",
            "guest_name",
            "guest_phone",
            "starts_at",
            "ends_at",
            "guest_count",
            "total_amount",
            "paid_amount",
            "refunded_amount",
            "status",
            "payment_status",
            "cancelled_at",
            "refunded_at",
            "created_by",
            "created_by_email",
            "notes",
            "created_at",
            "updated_at",
        ]


class VenueReservationWriteSerializer(serializers.Serializer):
    occasion_type = serializers.PrimaryKeyRelatedField(queryset=OccasionType.objects.all())
    guest_name = serializers.CharField(max_length=255)
    guest_phone = serializers.CharField(max_length=30)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    guest_count = serializers.IntegerField(min_value=1)
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        now = timezone.now()
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        total_amount = attrs.get("total_amount", getattr(self.instance, "total_amount", None))
        paid_amount = getattr(self.instance, "paid_amount", Decimal("0.00"))

        if starts_at and starts_at < now:
            raise serializers.ValidationError({"starts_at": "Start time cannot be in the past."})
        if ends_at and ends_at < now:
            raise serializers.ValidationError({"ends_at": "End time cannot be in the past."})
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})

        if total_amount is not None and paid_amount > total_amount:
            raise serializers.ValidationError({"paid_amount": "Paid amount cannot exceed total amount."})

        return attrs


class ReservationPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    note = serializers.CharField(required=False, allow_blank=True)


class ReservationCancelSerializer(serializers.Serializer):
    refund_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )
    note = serializers.CharField(required=False, allow_blank=True)

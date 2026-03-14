from decimal import Decimal

from rest_framework import serializers

from tickets.models import GateEntryDay, GateTicket, GateTicketSale, GateTicketType


class GateTicketTypeSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))

    class Meta:
        model = GateTicketType
        fields = ["id", "name", "price", "is_active", "display_order", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GateEntryDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = GateEntryDay
        fields = ["id", "visit_date", "daily_capacity", "is_open", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GateTicketSaleItemSerializer(serializers.Serializer):
    ticket_type = serializers.PrimaryKeyRelatedField(queryset=GateTicketType.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class GateTicketSaleCreateSerializer(serializers.Serializer):
    buyer_name = serializers.CharField(max_length=255)
    buyer_phone = serializers.CharField(max_length=30)
    visit_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = GateTicketSaleItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one ticket selection is required.")
        return value


class GateTicketReadSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.CharField(source="ticket_type.name", read_only=True)
    sale_id = serializers.IntegerField(source="sale.id", read_only=True)
    checked_in_by_email = serializers.CharField(source="checked_in_by.email", read_only=True)

    class Meta:
        model = GateTicket
        fields = [
            "id",
            "sale_id",
            "ticket_type",
            "ticket_type_name",
            "visit_date",
            "code",
            "status",
            "checked_in_at",
            "checked_in_by",
            "checked_in_by_email",
            "created_at",
        ]


class GateTicketSaleReadSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    tickets = GateTicketReadSerializer(many=True, read_only=True)

    class Meta:
        model = GateTicketSale
        fields = [
            "id",
            "buyer_name",
            "buyer_phone",
            "visit_date",
            "total_amount",
            "status",
            "created_by",
            "created_by_email",
            "notes",
            "created_at",
            "tickets",
        ]


class GateTicketCheckInSerializer(serializers.Serializer):
    pass


class GateTicketCheckInByCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class GateTicketVoidSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)

from rest_framework import serializers
from sales.models import Sale, SaleItem


class SaleItemReadSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "subtotal",
        ]


class SaleReadSerializer(serializers.ModelSerializer):
    items = SaleItemReadSerializer(many=True, read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    total_amount = serializers.SerializerMethodField()

    def get_total_amount(self, obj):
        return sum(item.subtotal for item in obj.items.all())

    class Meta:
        model = Sale
        fields = [
            "id",
            "status",
            "total_amount",
            "created_at",
            "created_by_email",
            "items",
        ]


class SaleCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Optional override (owner/manager only).",
    )


class SaleCreateSerializer(serializers.Serializer):
    items = SaleCreateItemSerializer(many=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Sale must contain at least one item.")
        return items

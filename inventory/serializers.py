from rest_framework import serializers
from inventory.models import StockMovement, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "sku",
            "cost_price",
            "selling_price",
            "stock_quantity",
            "is_active",
            "low_stock_threshold",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    direction = serializers.ChoiceField(
        choices=[("in", "In"), ("out", "Out")],
        required=False,
        help_text="Required only for adjustment movements"
    )

    class Meta:
        model = StockMovement
        fields = ["id", "product", "movement_type", "quantity", "direction", "note", "created_at"]

    def validate(self, attrs):
        movement_type = attrs.get("movement_type")
        direction = attrs.get("direction")

        if movement_type == "adjustment" and direction not in ("in", "out"):
            raise serializers.ValidationError("Adjustment movement requires direction: 'in' or 'out'.")

        if movement_type != "adjustment" and direction:
            raise serializers.ValidationError("Only adjustment movements can have a direction.")

        return attrs

from rest_framework import serializers
from inventory.models import StockMovement, Category, Product, LowStockAlert


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_name",
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


class LowStockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    recipient_users = serializers.SerializerMethodField()

    class Meta:
        model = LowStockAlert
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "triggered_by_movement",
            "threshold_value",
            "stock_quantity_at_trigger",
            "recipient_user_ids",
            "recipient_users",
            "is_active",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_recipient_users(self, obj):
        recipients = {
            user.id: {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
            }
            for user in obj.club.users.filter(id__in=obj.recipient_user_ids, is_active=True)
        }
        return [
            recipients[user_id]
            for user_id in obj.recipient_user_ids
            if user_id in recipients
        ]

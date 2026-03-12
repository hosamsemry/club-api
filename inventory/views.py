from core.views import TenantModelViewSet
from inventory.models import StockMovement, Category, Product
from inventory.serializers import StockMovementSerializer, CategorySerializer, ProductSerializer
from rest_framework import permissions
from inventory.services.stock_service import StockService
from core.permissions import RolePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

class StockMovementViewSet(TenantModelViewSet):
    queryset = StockMovement.objects.select_related(
        "product",
        "product__category",
        "created_by",
        "club",
    )
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]

    def perform_create(self, serializer):
        validated = serializer.validated_data

        movement = StockService.create_movement(
            product=validated["product"],
            movement_type=validated["movement_type"],
            quantity=validated["quantity"],
            direction=validated.get("direction"),
            user=self.request.user,
            note=validated.get("note", ""),
        )

        return movement

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("Stock movements cannot be updated")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("Stock movements cannot be updated")




class CategoryViewSet(TenantModelViewSet):
    queryset = Category.objects.select_related("club")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]


class ProductViewSet(TenantModelViewSet):
    queryset = Product.objects.select_related("category", "club")
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name", "sku"]

    def perform_create(self, serializer):
        product = serializer.save(club=self.request.user.club)
        if product.stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative on creation")
        return product

    def perform_update(self, serializer):
        product = serializer.save(club=self.request.user.club)
        if product.stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative after update")
        return product
    
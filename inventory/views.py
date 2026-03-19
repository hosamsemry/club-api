from core.views import TenantModelViewSet
from inventory.models import StockMovement, Category, Product, LowStockAlert
from inventory.serializers import (
    StockMovementSerializer,
    CategorySerializer,
    ProductSerializer,
    LowStockAlertSerializer,
)
from rest_framework import permissions
from inventory.services.stock_service import StockService
from core.permissions import RolePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

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


class LowStockAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LowStockAlert.objects.select_related(
        "product",
        "triggered_by_movement",
        "club",
    )
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active", "product"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.club_id:
            return LowStockAlert.objects.none()

        return super().get_queryset().filter(club=user.club)

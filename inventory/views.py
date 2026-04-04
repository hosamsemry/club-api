from django.core.cache import cache
from rest_framework.response import Response

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
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"stock_movements:{club_id}:{user_id}:*")
        cache.delete_pattern(f"products:{club_id}:{user_id}:*")
        return movement

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("Stock movements cannot be updated")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("Stock movements cannot be updated")
    
    def list(self, request, *args, **kwargs):
        user_id = request.user.id
        club_id = request.user.club_id

        query_string = request.GET.urlencode()
        cache_key = f"stock_movements:{club_id}:{user_id}:{query_string}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        cache.set(cache_key, response.data, timeout=60 * 5)

        return response




class CategoryViewSet(TenantModelViewSet):
    queryset = Category.objects.select_related("club")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]

    def perform_create(self, serializer):
        category = serializer.save(club=self.request.user.club)
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"categories:{club_id}:{user_id}:*")
        cache.delete_pattern(f"products:{club_id}:{user_id}:*")  

        return category
    
    def perform_update(self, serializer):
        category = serializer.save(club=self.request.user.club)
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"categories:{club_id}:{user_id}:*")
        cache.delete_pattern(f"products:{club_id}:{user_id}:*")  

        return category
    
    def perform_destroy(self, instance):
        if instance.products.exists():
            raise ValidationError("Cannot delete category that has products assigned to it. Please reassign or permanently delete all products first.")
        
        instance.delete()
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"categories:{club_id}:{user_id}:*")
        cache.delete_pattern(f"products:{club_id}:{user_id}:*")

    def list(self, request, *args, **kwargs):
        user_id = request.user.id
        club_id = request.user.club_id

        query_string = request.GET.urlencode()
        cache_key = f"categories:{club_id}:{user_id}:{query_string}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        cache.set(cache_key, response.data, timeout=60 * 5)

        return response


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
        
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"products:{club_id}:{user_id}:*")

        return product

    def perform_update(self, serializer):
        product = serializer.save(club=self.request.user.club)
        if product.stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative after update")
        
        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"products:{club_id}:{user_id}:*")

        return product
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

        club_id = self.request.user.club_id
        user_id = self.request.user.id

        cache.delete_pattern(f"products:{club_id}:{user_id}:*")
    
    def list(self, request, *args, **kwargs):
        user_id = request.user.id
        club_id = request.user.club_id

        query_string = request.GET.urlencode()
        cache_key = f"products:{club_id}:{user_id}:{query_string}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        cache.set(cache_key, response.data, timeout=60 * 5)

        return response


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

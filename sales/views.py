from rest_framework import status, permissions
from rest_framework.response import Response
from core.views import TenantModelViewSet
from core.permissions import RolePermission
from sales.models import Sale
from sales.serializers import SaleCreateSerializer, SaleReadSerializer
from sales.services.sale_service import SaleService
from rest_framework.decorators import action

class SaleViewSet(TenantModelViewSet):
    queryset = Sale.objects.select_related("created_by").prefetch_related("items__product")
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        return SaleReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sale = SaleService.create_sale(
            club=request.user.club,
            user=request.user,
            items=serializer.validated_data["items"],
            note=serializer.validated_data.get("note", ""),
        )

        output = SaleReadSerializer(sale, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, RolePermission])
    def refund(self, request, pk=None):
        if request.user.role not in ["owner", "manager"]:
            return Response({"detail": "Only owner/manager can refund sales."}, status=status.HTTP_403_FORBIDDEN)

        sale = SaleService.refund_sale(
            club=request.user.club,
            user=request.user,
            sale_id=pk,
            note=request.data.get("note", "")
        )

        output = SaleReadSerializer(sale, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)
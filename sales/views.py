import datetime
from zoneinfo import ZoneInfo
from django.db.models.functions import Greatest
from inventory.models import Product

from django.core.cache import cache

from rest_framework import status, permissions
from rest_framework.response import Response
from core.views import TenantModelViewSet
from core.permissions import RolePermission
from sales.models import Sale, SaleItem
from sales.serializers import SaleCreateSerializer, SaleReadSerializer
from sales.services.sale_service import SaleService
from rest_framework.decorators import action
from .filters import SaleFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.utils import timezone
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper, Case, When, Value, BooleanField


class SaleViewSet(TenantModelViewSet):
    queryset = Sale.objects.select_related("created_by").prefetch_related(
        "items__product"
    )
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier"]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = SaleFilter
    ordering_fields = ["created_at", "total_amount", "status"]
    ordering = ["-created_at"]
    search_fields = ["created_by__email", "items__product__name", "items__product__sku"]

    def get_queryset(self):
        return super().get_queryset().distinct()

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
        for item in serializer.validated_data["items"]:
            qty = item["quantity"]
            Product.objects.filter(pk=item["product_id"]).update(
                total_sold_30d=F("total_sold_30d") + qty,
                is_best_seller=Case(
                    When(total_sold_30d__gte=max(0, 10 - qty), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )

        output = SaleReadSerializer(sale, context=self.get_serializer_context())
        club_id = request.user.club_id
        cache.delete_pattern(f"products:{club_id}:*")
        cache.delete_pattern(f"stock_movements:{club_id}:*")
        cache.delete(f"dashboard_summary:{club_id}")
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, RolePermission],
    )
    def refund(self, request, pk=None):
        if request.user.role not in ["owner", "manager"]:
            return Response(
                {"detail": "Only owner/manager can refund sales."},
                status=status.HTTP_403_FORBIDDEN,
            )

        sale = SaleService.refund_sale(
            club=request.user.club,
            user=request.user,
            sale_id=pk,
            note=request.data.get("note", ""),
        )

        for item in sale.items.all():
            qty = item.quantity
            Product.objects.filter(pk=item.product_id).update(
                total_sold_30d=Greatest(0, F("total_sold_30d") - qty),
            )

        club_id = request.user.club_id
        cache.delete_pattern(f"products:{club_id}:*")
        cache.delete_pattern(f"stock_movements:{club_id}:*")
        cache.delete(f"dashboard_summary:{club_id}")

        output = SaleReadSerializer(sale, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        date_str = request.query_params.get("date")
        club_timezone = ZoneInfo(request.user.club.timezone or "UTC") if (request.user and request.user.club) else ZoneInfo("UTC")
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().astimezone(club_timezone).date()

        day_start = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=club_timezone)
        day_end = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=club_timezone)

        qs = (
            super()
            .get_queryset()
            .filter(created_at__gte=day_start, created_at__lte=day_end, status="completed")
        )

        totals = qs.aggregate(
            total_revenue=Sum("total_amount"),
            sales_count=Count("id"),
        )

        by_cashier = (
            qs.values("created_by_id", "created_by__email")
            .annotate(
                revenue=Sum("total_amount"),
                count=Count("id"),
            )
            .order_by("-revenue")
        )

        return Response(
            {
                "date": str(target_date),
                "total_revenue": totals["total_revenue"] or 0,
                "sales_count": totals["sales_count"],
                "by_cashier": list(by_cashier),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="daily-profit")
    def daily_profit(self, request):
        if request.user.role not in ["owner", "manager"]:
            return Response(
                {"detail": "Only owner/manager can view profit analytics."},
                status=status.HTTP_403_FORBIDDEN,
            )

        date_str = request.query_params.get("date")
        club_timezone = ZoneInfo(request.user.club.timezone or "UTC") if (request.user and request.user.club) else ZoneInfo("UTC")
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().astimezone(club_timezone).date()

        day_start = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=club_timezone)
        day_end = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=club_timezone)

        sales_qs = (
            super()
            .get_queryset()
            .filter(
                created_at__gte=day_start,
                created_at__lte=day_end,
                status="completed",
            )
        )

        items_qs = SaleItem.objects.filter(sale__in=sales_qs).annotate(
            estimated_profit=ExpressionWrapper(
                (F("unit_price") - F("cost_price")) * F("quantity"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

        totals = items_qs.aggregate(
            total_revenue=Sum("subtotal"),
            total_cost=Sum(
                ExpressionWrapper(
                    F("cost_price") * F("quantity"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            total_profit=Sum("estimated_profit"),
        )

        return Response(
            {
                "date": str(target_date),
                "total_revenue": totals["total_revenue"] or 0,
                "total_cost": totals["total_cost"] or 0,
                "total_profit": totals["total_profit"] or 0,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="top-products")
    def top_products(self, request):
        if request.user.role not in ["owner", "manager"]:
            return Response(
                {"detail": "Only owner/manager can view top-selling products."},
                status=status.HTTP_403_FORBIDDEN,
            )

        date_str = request.query_params.get("date")
        club_timezone = ZoneInfo(request.user.club.timezone or "UTC") if (request.user and request.user.club) else ZoneInfo("UTC")
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().astimezone(club_timezone).date()

        day_start = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=club_timezone)
        day_end = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=club_timezone)

        sales_qs = (
            super()
            .get_queryset()
            .filter(
                created_at__gte=day_start,
                created_at__lte=day_end,
                status="completed",
            )
        )

        top_products = (
            SaleItem.objects.filter(sale__in=sales_qs)
            .annotate(
                product_name=F("product__name"),
                product_sku=F("product__sku"),
            )
            .values(
                "product_id",
                "product_name",
                "product_sku",
            )
            .annotate(
                total_quantity_sold=Sum("quantity"),
                total_revenue=Sum("subtotal"),
            )
            .order_by("-total_quantity_sold", "-total_revenue")
        )

        return Response(
            {
                "date": str(target_date),
                "results": list(top_products),
            },
            status=status.HTTP_200_OK,
        )

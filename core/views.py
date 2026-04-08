from decimal import Decimal
from zoneinfo import ZoneInfo
from django.db.models import Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from core.models import AuditLog
from core.permissions import RolePermission
from core.serializers import (
    AuditLogSerializer,
    DashboardSummarySerializer,
)
from events.models import VenueReservation
from inventory.models import LowStockAlert, Product
from tickets.models import GateTicket, GateTicketSale

class TenantModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return super().get_queryset().none()
        return super().get_queryset().filter(
            club=self.request.user.club
        )

    def perform_create(self, serializer):
        serializer.save(club=self.request.user.club)

    def perform_update(self, serializer):
        serializer.save(club=self.request.user.club)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet, TenantModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["action", "user"]
    search_fields = ["details", "path", "method", "ip_address"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.club_id:
            return AuditLog.objects.none()

        queryset = (
            AuditLog.objects.select_related("user", "club")
            .filter(club=user.club)
            .order_by("-created_at")
        )

        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        start_date = self.request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        end_date = self.request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset


class DashboardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DashboardSummarySerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]

    def list(self, request, *args, **kwargs):
        cache_key = f"dashboard_summary:{request.user.club_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        user = request.user
        if not user.is_authenticated or not user.club_id:
            return Response({"detail": "Unauthorized"}, status=401)

        club = user.club
        club_timezone = ZoneInfo(club.timezone or "UTC")
        today = timezone.now().astimezone(club_timezone).date()

        today_ticket_sales = GateTicketSale.objects.filter(
            club=club,
            visit_date=today,
            status=GateTicketSale.STATUS_ISSUED,
        )
        today_ticket_revenue = (
            today_ticket_sales.aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        data = {
            "total_products": Product.objects.filter(club=club, is_active=True).count(),
            "low_stock_alert_count": LowStockAlert.objects.filter(
                club=club,
                is_active=True,
            ).count(),
            "today_reservations_count": VenueReservation.objects.filter(
                club=club,
                starts_at__date=today,
            ).exclude(status=VenueReservation.STATUS_CANCELLED).count(),
            "pending_reservations_count": VenueReservation.objects.filter(
                club=club,
                status=VenueReservation.STATUS_PENDING,
            ).count(),
            "today_ticket_sales_count": today_ticket_sales.count(),
            "today_ticket_revenue": today_ticket_revenue,
            "today_checked_in_tickets_count": GateTicket.objects.filter(
                club=club,
                visit_date=today,
                status=GateTicket.STATUS_CHECKED_IN,
            ).count(),
            "recent_activity": AuditLog.objects.filter(club=club)
            .order_by("-created_at")[:5]
            .values("action", "user__email", "created_at"),
        }
        for item in data["recent_activity"]:
            item["user_email"] = item.pop("user__email")

        serializer = self.get_serializer(data)
        cache.set(cache_key, serializer.data, timeout=300)  # Cache for 5 minutes
        return Response(serializer.data)

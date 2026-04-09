from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from core.permissions import RolePermission
from core.views import TenantModelViewSet
from tickets.filters import GateEntryDayFilter, GateTicketFilter, GateTicketSaleFilter
from tickets.models import GateEntryDay, GateTicket, GateTicketSale, GateTicketType
from tickets.serializers import (
    GateEntryDaySerializer,
    GateTicketCheckInByCodeSerializer,
    GateTicketCheckInSerializer,
    GateTicketReadSerializer,
    GateTicketSaleCreateSerializer,
    GateTicketSaleReadSerializer,
    GateTicketTypeSerializer,
    GateTicketVoidSerializer,
)
from tickets.services.gate_ticket_service import GateTicketService


class GateTicketTypeViewSet(TenantModelViewSet):
    queryset = GateTicketType.objects.select_related("club")
    serializer_class = GateTicketTypeSerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ["is_active"]
    ordering_fields = ["display_order", "name", "created_at"]
    ordering = ["display_order", "name"]
    search_fields = ["name"]

    def perform_create(self, serializer):
        ticket_type = serializer.save(club=self.request.user.club)
        GateTicketService.log_ticket_type_created(ticket_type=ticket_type, user=self.request.user)

    def perform_update(self, serializer):
        current = self.get_object()
        was_active = current.is_active
        ticket_type = serializer.save(club=self.request.user.club)
        GateTicketService.log_ticket_type_updated(
            ticket_type=ticket_type,
            user=self.request.user,
            deactivated=was_active and not ticket_type.is_active,
        )

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Ticket types cannot be deleted.")


class GateEntryDayViewSet(TenantModelViewSet):
    queryset = GateEntryDay.objects.select_related("club")
    serializer_class = GateEntryDaySerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = GateEntryDayFilter
    ordering_fields = ["visit_date", "daily_capacity", "created_at"]
    ordering = ["-visit_date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.club_id:
            GateEntryDay.objects.filter(
                club=user.club,
                visit_date__lt=timezone.localdate(),
                is_open=True,
            ).update(is_open=False)
        return queryset.annotate(
            sold_tickets=Count(
                "club__tickets_gatetickets",
                filter=Q(
                    club__tickets_gatetickets__visit_date=F("visit_date"),
                    club__tickets_gatetickets__status__in=[
                        GateTicket.STATUS_ISSUED,
                        GateTicket.STATUS_CHECKED_IN,
                    ],
                ),
            ),
            checked_in_tickets=Count(
                "club__tickets_gatetickets",
                filter=Q(
                    club__tickets_gatetickets__visit_date=F("visit_date"),
                    club__tickets_gatetickets__status=GateTicket.STATUS_CHECKED_IN,
                ),
            ),
        )

    def perform_create(self, serializer):
        entry_day = serializer.save(club=self.request.user.club)
        GateTicketService.log_entry_day_created(entry_day=entry_day, user=self.request.user)

    def perform_update(self, serializer):
        entry_day = serializer.save(club=self.request.user.club)
        GateTicketService.log_entry_day_updated(entry_day=entry_day, user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Entry days cannot be deleted.")


class GateTicketSaleViewSet(TenantModelViewSet):
    queryset = GateTicketSale.objects.select_related("club", "created_by").prefetch_related(
        "tickets__ticket_type"
    )
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier", "staff"]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = GateTicketSaleFilter
    ordering_fields = ["visit_date", "created_at", "total_amount"]
    ordering = ["-created_at"]
    search_fields = ["buyer_name", "buyer_phone", "notes"]

    def get_serializer_class(self):
        if self.action == "create":
            return GateTicketSaleCreateSerializer
        return GateTicketSaleReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = GateTicketService.create_sale(
            club=request.user.club,
            user=request.user,
            **serializer.validated_data,
        )
        output = GateTicketSaleReadSerializer(sale, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Ticket sales cannot be edited.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Ticket sales cannot be edited.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Ticket sales cannot be deleted.")

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                target_date = timezone.datetime.fromisoformat(date_str).date()
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.localdate()

        qs = super().get_queryset().filter(
            visit_date=target_date,
            status=GateTicketSale.STATUS_ISSUED,
        )

        totals = qs.aggregate(
            total_revenue=Sum("total_amount"),
            ticket_sales_count=Count("id"),
        )

        return Response(
            {
                "date": str(target_date),
                "ticket_sales_count": totals["ticket_sales_count"],
                "total_revenue": totals["total_revenue"] or 0,
            },
            status=status.HTTP_200_OK,
        )


class GateTicketViewSet(TenantModelViewSet):
    queryset = GateTicket.objects.select_related(
        "sale",
        "ticket_type",
        "checked_in_by",
        "club",
    )
    serializer_class = GateTicketReadSerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager", "cashier", "staff"]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = GateTicketFilter
    ordering_fields = ["visit_date", "created_at", "status"]
    ordering = ["-created_at"]
    search_fields = ["code", "sale__buyer_name", "sale__buyer_phone", "ticket_type__name"]

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        ticket = self.get_object()
        serializer = GateTicketCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = GateTicketService.check_in_ticket(ticket=ticket, user=request.user)
        output = GateTicketReadSerializer(ticket, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="check-in-by-code")
    def check_in_by_code(self, request):
        serializer = GateTicketCheckInByCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = GateTicketService.check_in_ticket_by_code(
            club=request.user.club,
            user=request.user,
            code=serializer.validated_data["code"],
        )
        output = GateTicketReadSerializer(ticket, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        ticket = self.get_object()
        serializer = GateTicketVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = GateTicketService.void_ticket(
            ticket=ticket,
            user=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        output = GateTicketReadSerializer(ticket, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Create tickets through ticket sales.")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Tickets cannot be edited.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Tickets cannot be edited.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Tickets cannot be deleted.")

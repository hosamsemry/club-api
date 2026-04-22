from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from django.core.cache import cache
from core.permissions import RolePermission
from core.views import TenantModelViewSet
from events.filters import VenueReservationFilter
from events.models import OccasionType, VenueReservation
from events.serializers import (
    OccasionTypeSerializer,
    ReservationCancelSerializer,
    ReservationPaymentSerializer,
    VenueReservationReadSerializer,
    VenueReservationWriteSerializer,
)
from events.services.reservation_service import ReservationService


def invalidate_occasion_type_cache(club_id):
    cache.delete_pattern(f"occasion_types:{club_id}:*")


def invalidate_venue_reservation_cache(club_id):
    cache.delete_pattern(f"venue_reservations:{club_id}:*")
    cache.delete(f"dashboard_summary:{club_id}")


class OccasionTypeViewSet(TenantModelViewSet):
    queryset = OccasionType.objects.select_related("club")
    serializer_class = OccasionTypeSerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def perform_create(self, serializer):
        occasion_type = serializer.save(club=self.request.user.club)
        ReservationService.log_occasion_type_created(
            occasion_type=occasion_type,
            user=self.request.user,
        )
        club_id = self.request.user.club_id
        invalidate_occasion_type_cache(club_id)

    def perform_update(self, serializer):
        previous = self.get_object()
        was_active = previous.is_active
        occasion_type = serializer.save(club=self.request.user.club)
        ReservationService.log_occasion_type_updated(
            occasion_type=occasion_type,
            user=self.request.user,
            deactivated=was_active and not occasion_type.is_active,
        )
        club_id = self.request.user.club_id
        invalidate_occasion_type_cache(club_id)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Occasion types cannot be deleted.")
    
    def list(self, request, *args, **kwargs):
        club_id = request.user.club_id

        query_string = request.GET.urlencode()
        cache_key = f"occasion_types:{club_id}:{query_string}"
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=3600)
        return response


class VenueReservationViewSet(TenantModelViewSet):
    queryset = VenueReservation.objects.select_related(
        "occasion_type",
        "club",
        "created_by",
    )
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = VenueReservationFilter
    ordering_fields = ["starts_at", "ends_at", "created_at", "total_amount", "paid_amount"]
    ordering = ["-starts_at"]
    search_fields = ["guest_name", "guest_phone", "occasion_type__name", "notes"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.club_id:
            ReservationService.cancel_expired_pending_reservations(club=user.club)
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VenueReservationWriteSerializer
        if self.action == "record_payment":
            return ReservationPaymentSerializer
        if self.action == "cancel":
            return ReservationCancelSerializer
        return VenueReservationReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = ReservationService.create_reservation(
            club=request.user.club,
            user=request.user,
            paid_amount=0,
            **serializer.validated_data,
        )
        output = VenueReservationReadSerializer(reservation, context=self.get_serializer_context())
        club_id = request.user.club_id
        invalidate_venue_reservation_cache(club_id)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        data = {
            "occasion_type": serializer.validated_data.get("occasion_type", instance.occasion_type),
            "guest_name": serializer.validated_data.get("guest_name", instance.guest_name),
            "guest_phone": serializer.validated_data.get("guest_phone", instance.guest_phone),
            "starts_at": serializer.validated_data.get("starts_at", instance.starts_at),
            "ends_at": serializer.validated_data.get("ends_at", instance.ends_at),
            "guest_count": serializer.validated_data.get("guest_count", instance.guest_count),
            "total_amount": serializer.validated_data.get("total_amount", instance.total_amount),
            "paid_amount": instance.paid_amount,
            "notes": serializer.validated_data.get("notes", instance.notes),
        }
        reservation = ReservationService.update_reservation(
            reservation=instance,
            user=request.user,
            **data,
        )
        output = VenueReservationReadSerializer(reservation, context=self.get_serializer_context())
        club_id = request.user.club_id
        invalidate_venue_reservation_cache(club_id)
        return Response(output.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        club_id = request.user.club_id
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        reservation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = ReservationService.record_payment(
            reservation=reservation,
            user=request.user,
            amount=serializer.validated_data["amount"],
            note=serializer.validated_data.get("note", ""),
        )
        output = VenueReservationReadSerializer(reservation, context=self.get_serializer_context())
        club_id = request.user.club_id
        invalidate_venue_reservation_cache(club_id)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = ReservationService.cancel_reservation(
            reservation=reservation,
            user=request.user,
            refund_amount=serializer.validated_data.get("refund_amount"),
            note=serializer.validated_data.get("note", ""),
        )
        output = VenueReservationReadSerializer(reservation, context=self.get_serializer_context())
        club_id = request.user.club_id
        invalidate_venue_reservation_cache(club_id)
        return Response(output.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Reservations cannot be deleted.")
    
    def list(self, request, *args, **kwargs):
        club_id = request.user.club_id
        expired_count = ReservationService.cancel_expired_pending_reservations(
            club=request.user.club
        )
        if expired_count:
            invalidate_venue_reservation_cache(club_id)

        query_string = request.GET.urlencode()
        cache_key = f"venue_reservations:{club_id}:{query_string}"
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=3600)
        return response

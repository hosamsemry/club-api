from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.models import AuditLog
from core.permissions import RolePermission
from core.serializers import AuditLogSerializer
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend


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

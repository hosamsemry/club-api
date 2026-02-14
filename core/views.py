from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from core.permissions import RolePermission
from .serializers import (
    RegisterSerializer,
    ClubUserReadSerializer,
    ClubUserCreateSerializer,
    ClubUserUpdateSerializer,
)

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        return token


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(ModelViewSet):
    serializer_class = RegisterSerializer
    permission_classes = []
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class ClubUserViewSet(ModelViewSet):
    """
    GET    /api/accounts/users/        — list all users in the authenticated user's club
    POST   /api/accounts/users/        — create a new user in the same club
    GET    /api/accounts/users/{id}/   — retrieve a single user
    PATCH  /api/accounts/users/{id}/   — update role / active status
    """

    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return User.objects.filter(club=self.request.user.club).order_by("email")

    def get_serializer_class(self):
        if self.action == "create":
            return ClubUserCreateSerializer
        if self.action in ("partial_update", "update"):
            return ClubUserUpdateSerializer
        return ClubUserReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            ClubUserReadSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(ClubUserReadSerializer(user).data)

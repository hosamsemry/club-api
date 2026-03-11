from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    def has_permission(self, request, view):
        required_roles = getattr(view, "required_roles", [])
        return (
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.role in required_roles)
        )

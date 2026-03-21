from rest_framework.routers import DefaultRouter

from core.views import AuditLogViewSet, DashboardViewSet


router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="auditlog")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls

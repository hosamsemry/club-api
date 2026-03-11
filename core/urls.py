from rest_framework.routers import DefaultRouter

from core.views import AuditLogViewSet


router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="auditlog")

urlpatterns = router.urls

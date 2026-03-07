from rest_framework.routers import DefaultRouter
from sales.views import SaleViewSet

router = DefaultRouter()
router.register(r"", SaleViewSet, basename="sale")

urlpatterns = router.urls
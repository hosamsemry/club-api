from rest_framework.routers import DefaultRouter
from inventory.views import (
    CategoryViewSet,
    ProductViewSet,
    StockMovementViewSet,
    LowStockAlertViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"stock-movements", StockMovementViewSet, basename="stockmovement")
router.register(r"low-stock-alerts", LowStockAlertViewSet, basename="lowstockalert")

urlpatterns = router.urls

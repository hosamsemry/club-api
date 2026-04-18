from rest_framework.routers import DefaultRouter

from reporting.views import DailyClubReportViewSet, RevenueViewSet, TransactionsViewSet


router = DefaultRouter()
router.register(r"daily", DailyClubReportViewSet, basename="dailyclubreport")
router.register(r"revenue", RevenueViewSet, basename="revenue")
router.register(r"transactions", TransactionsViewSet, basename="transactions")

urlpatterns = router.urls

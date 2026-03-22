from rest_framework.routers import DefaultRouter

from reporting.views import DailyClubReportViewSet, RevenueViewSet


router = DefaultRouter()
router.register(r"daily", DailyClubReportViewSet, basename="dailyclubreport")
router.register(r"revenue", RevenueViewSet, basename="revenue")

urlpatterns = router.urls

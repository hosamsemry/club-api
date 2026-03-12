from rest_framework.routers import DefaultRouter

from reporting.views import DailyClubReportViewSet


router = DefaultRouter()
router.register(r"daily", DailyClubReportViewSet, basename="dailyclubreport")

urlpatterns = router.urls

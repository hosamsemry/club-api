from rest_framework.routers import DefaultRouter

from tickets.views import GateEntryDayViewSet, GateTicketSaleViewSet, GateTicketTypeViewSet, GateTicketViewSet


router = DefaultRouter()
router.register(r"types", GateTicketTypeViewSet, basename="gatetickettype")
router.register(r"days", GateEntryDayViewSet, basename="gateentryday")
router.register(r"sales", GateTicketSaleViewSet, basename="gateticketsale")
router.register(r"items", GateTicketViewSet, basename="gateticket")

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from events.views import OccasionTypeViewSet, VenueReservationViewSet


router = DefaultRouter()
router.register(r"occasion-types", OccasionTypeViewSet, basename="occasiontype")
router.register(r"reservations", VenueReservationViewSet, basename="venuereservation")

urlpatterns = router.urls

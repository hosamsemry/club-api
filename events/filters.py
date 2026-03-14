import django_filters

from events.models import VenueReservation


class VenueReservationFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="starts_at", lookup_expr="date__gte")
    end_date = django_filters.DateFilter(field_name="ends_at", lookup_expr="date__lte")
    payment_status = django_filters.CharFilter(field_name="payment_status")
    status = django_filters.CharFilter(field_name="status")
    occasion_type = django_filters.NumberFilter(field_name="occasion_type_id")
    guest_phone = django_filters.CharFilter(field_name="guest_phone", lookup_expr="icontains")

    class Meta:
        model = VenueReservation
        fields = ["status", "payment_status", "occasion_type", "guest_phone", "start_date", "end_date"]

import django_filters

from tickets.models import GateEntryDay, GateTicket, GateTicketSale


class GateEntryDayFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="visit_date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="visit_date", lookup_expr="lte")
    is_open = django_filters.BooleanFilter(field_name="is_open")

    class Meta:
        model = GateEntryDay
        fields = ["start_date", "end_date", "is_open"]


class GateTicketSaleFilter(django_filters.FilterSet):
    visit_date = django_filters.DateFilter(field_name="visit_date")
    buyer_phone = django_filters.CharFilter(field_name="buyer_phone", lookup_expr="icontains")
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = GateTicketSale
        fields = ["visit_date", "buyer_phone", "created_by", "status"]


class GateTicketFilter(django_filters.FilterSet):
    visit_date = django_filters.DateFilter(field_name="visit_date")
    status = django_filters.CharFilter(field_name="status")
    ticket_type = django_filters.NumberFilter(field_name="ticket_type_id")
    code = django_filters.CharFilter(field_name="code", lookup_expr="icontains")

    class Meta:
        model = GateTicket
        fields = ["visit_date", "status", "ticket_type", "code"]

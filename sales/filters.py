import django_filters
from sales.models import Sale


class SaleFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    end_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    status = django_filters.CharFilter(field_name="status")
    created_by = django_filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = Sale
        fields = ["status", "created_by", "start_date", "end_date"]
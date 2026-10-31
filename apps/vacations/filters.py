import django_filters

from .models import VacationRequest


class VacationRequestFilter(django_filters.FilterSet):
    """date_from / date_to — заявки, що перетинаються з періодом (для календаря)."""

    date_from = django_filters.DateFilter(field_name="date_end", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date_start", lookup_expr="lte")

    class Meta:
        model = VacationRequest
        fields = ["employee", "status", "vacation_type"]

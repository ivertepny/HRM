import django_filters
from django.db.models import Q

from .models import Equipment, EquipmentAssignment


class EquipmentFilter(django_filters.FilterSet):
    state = django_filters.ChoiceFilter(
        choices=Equipment.State.choices, method="filter_state"
    )
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Equipment
        fields = ["category", "holder"]

    def filter_state(self, queryset, name, value):
        return queryset.filter(Equipment.state_q(value))

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(serial_number__icontains=value)
        )


class EquipmentAssignmentFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(
        field_name="date_returned", lookup_expr="isnull"
    )

    class Meta:
        model = EquipmentAssignment
        fields = ["employee", "equipment"]

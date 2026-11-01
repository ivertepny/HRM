import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.company.models import StructuralUnit

from .models import Employee


class EmployeeFilter(django_filters.FilterSet):
    unit = django_filters.ModelChoiceFilter(
        queryset=StructuralUnit.objects.all(),
        method="filter_unit",
        label="Підрозділ разом з дочірніми",
    )
    active = django_filters.BooleanFilter(
        method="filter_active", label="Лише ті, хто працює зараз (без звільнених)"
    )

    class Meta:
        model = Employee
        fields = ["user", "structural_unit", "position", "level"]

    def filter_unit(self, queryset, name, unit):
        subtree = unit.get_descendants(include_self=True)
        return queryset.filter(structural_unit__in=subtree)

    def filter_active(self, queryset, name, value):
        working = Q(date_fired__isnull=True) | Q(date_fired__gt=timezone.localdate())
        return queryset.filter(working) if value else queryset.exclude(working)

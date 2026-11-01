import django_filters

from .models import User


class UserFilter(django_filters.FilterSet):
    has_employee = django_filters.BooleanFilter(
        field_name="employee_profile",
        lookup_expr="isnull",
        exclude=True,
        label="Має профіль працівника",
    )

    class Meta:
        model = User
        fields = ["status"]

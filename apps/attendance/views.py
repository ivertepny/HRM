import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.access.permissions import HasPermission
from apps.access.services import get_access, scope_queryset
from apps.company.models import StructuralUnit
from apps.employees.models import Employee

from .models import AttendanceRecord
from .report import build_report, employees_in_month, month_bounds, parse_month
from .serializers import AttendanceRecordSerializer, ReportSerializer


class AttendanceRecordFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = AttendanceRecord
        fields = ["employee", "status"]


@extend_schema_view(
    list=extend_schema(
        summary="Відмітки присутності",
        description="Свої — завжди; чужі — з attendance:read (у межах scope).",
    ),
    create=extend_schema(
        summary="Відмітитись",
        description="Лише за себе (attendance:write); одна відмітка на день.",
    ),
    partial_update=extend_schema(
        summary="Виправити свою відмітку",
        description="Лише власну і не старшу за ATTENDANCE_EDIT_DAYS днів.",
    ),
    destroy=extend_schema(summary="Видалити свою відмітку"),
)
@extend_schema(tags=["Attendance"])
class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "employee__user", "employee__structural_unit"
    )
    serializer_class = AttendanceRecordSerializer
    permission_classes = [HasPermission]
    required_permissions = {
        "read": "attendance:read",
        "write": "attendance:write",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_class = AttendanceRecordFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "attendance:read",
            unit_field="employee__structural_unit",
            owner=Q(employee__user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.employee.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.employee.structural_unit

    def _ensure_own_and_editable(self, record):
        # attendance:write — лише за себе: HR з цим дозволом чужий табель не править
        if not self.is_owner(record):
            raise PermissionDenied("Змінювати можна лише власний табель.")
        if not record.is_editable():
            raise ValidationError({"date": "Табель за цей день уже закрито для змін."})

    def perform_update(self, serializer):
        self._ensure_own_and_editable(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_own_and_editable(instance)
        instance.delete()

    @extend_schema(
        summary="Місячний звіт",
        description=(
            "Працівники в межах scope attendance:read: дні в офісі, віддалено, "
            "вихідні, відпустка, пропущені робочі дні, години."
        ),
        parameters=[
            OpenApiParameter("month", OpenApiTypes.STR, description="YYYY-MM"),
            OpenApiParameter(
                "unit", OpenApiTypes.INT, description="Підрозділ разом з дочірніми"
            ),
        ],
        responses={200: ReportSerializer},
    )
    @action(detail=False, methods=["get"])
    def report(self, request):
        # HasPermission пускає власника на будь-який GET — звіт лише з дозволом
        if not get_access(request).has_anywhere("attendance:read"):
            raise PermissionDenied("Потрібен дозвіл attendance:read.")
        try:
            first = parse_month(request.query_params.get("month"))
        except ValueError:
            raise ValidationError({"month": "Формат місяця — YYYY-MM."}) from None
        employees = scope_queryset(
            request,
            Employee.objects.all(),
            "attendance:read",
            unit_field="structural_unit",
        )
        unit_id = request.query_params.get("unit")
        if unit_id:
            unit = StructuralUnit.objects.filter(pk=unit_id).first()
            if unit is None:
                raise ValidationError({"unit": "Підрозділ не знайдено."})
            employees = employees.filter(
                structural_unit__in=unit.get_descendants(include_self=True)
            )
        employees = employees_in_month(employees, *month_bounds(first))
        report = build_report(employees, first)
        return Response(ReportSerializer(report).data)

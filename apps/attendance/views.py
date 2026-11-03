import csv

import django_filters
from django.db.models import Q
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.access.permissions import HasPermission
from apps.access.services import get_access, scope_queryset
from apps.company.models import StructuralUnit
from apps.employees.models import Employee

from .models import AttendanceRecord, Holiday
from .report import build_report, employees_in_month, month_bounds, parse_month
from .serializers import AttendanceRecordSerializer, HolidaySerializer, ReportSerializer

REPORT_PARAMETERS = [
    OpenApiParameter("month", OpenApiTypes.STR, description="YYYY-MM"),
    OpenApiParameter(
        "unit", OpenApiTypes.INT, description="Підрозділ разом з дочірніми"
    ),
]

CSV_COLUMNS = [
    ("Працівник", lambda row: str(row["employee"])),
    ("Email", lambda row: row["employee"].user.email),
    ("Підрозділ", lambda row: row["unit"]),
    ("Офіс", lambda row: row["office"]),
    ("Віддалено", lambda row: row["remote"]),
    ("Не працював", lambda row: row["off"]),
    ("Відпустка", lambda row: row["vacation"]),
    ("Без відмітки", lambda row: row["missing"]),
    # Кома — десятковий роздільник української локалі Excel
    ("Години", lambda row: f"{row['hours']:g}".replace(".", ",")),
]


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Захист від CSV-ін'єкції: Excel виконує клітинки, що починаються з = + - @."""
    text = str(value)
    if text[:1] in FORMULA_PREFIXES:
        return "'" + text
    return text


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

    def _report(self, request):
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
        return build_report(employees, first)

    @extend_schema(
        summary="Місячний звіт",
        description=(
            "Працівники в межах scope attendance:read: дні в офісі, віддалено, "
            "вихідні, відпустка, пропущені робочі дні, години. Робочі дні — "
            "пн–пт без святкових (holidays)."
        ),
        parameters=REPORT_PARAMETERS,
        responses={200: ReportSerializer},
    )
    @action(detail=False, methods=["get"])
    def report(self, request):
        return Response(ReportSerializer(self._report(request)).data)

    @extend_schema(
        summary="Місячний звіт у CSV",
        description=(
            "Ті самі дані, що й report, — для Excel: UTF-8 з BOM, роздільник «;», "
            "десяткова кома."
        ),
        parameters=REPORT_PARAMETERS,
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
    @action(detail=False, methods=["get"], url_path="report/csv")
    def report_csv(self, request):
        report = self._report(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="tabel-{report["month"]}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        # BOM — щоб Excel відкрив кирилицю як UTF-8
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow([title for title, _ in CSV_COLUMNS])
        for row in report["rows"]:
            writer.writerow([csv_safe(value(row)) for _, value in CSV_COLUMNS])
        return response


class HolidayPermission(permissions.BasePermission):
    """Читати — будь-кому з входом (табель показує свята всім); змінювати —
    лише з attendance:manage на всю компанію: свята спільні для всіх підрозділів,
    тож scoped-роль на один відділ їх не змінює."""

    message = "Потрібен дозвіл attendance:manage на всю компанію."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return get_access(request).has("attendance:manage")


class HolidayFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(field_name="date", lookup_expr="year")
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Holiday
        fields = []


@extend_schema_view(
    list=extend_schema(
        summary="Святкові (неробочі) дні",
        description="Бачать усі з входом; змінювати — attendance:manage.",
    ),
)
@extend_schema(tags=["Attendance"])
class HolidayViewSet(viewsets.ModelViewSet):
    """Календар неробочих днів компанії — його веде HR (див. Holiday)."""

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [HolidayPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = HolidayFilter
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

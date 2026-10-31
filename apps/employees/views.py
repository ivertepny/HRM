from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets

from apps.access.permissions import HasPermission, ensure_permission
from apps.access.services import scope_queryset

from .models import CareerHistory, Employee, EmployeeDocument, Position
from .serializers import (
    CareerHistorySerializer,
    EmployeeDocumentSerializer,
    EmployeeSerializer,
    PositionSerializer,
)


@extend_schema_view(
    create=extend_schema(
        summary="Create a new position",
        description="Adds a new position to the system.",
    )
)
class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.order_by("name")
    serializer_class = PositionSerializer
    permission_classes = [HasPermission]
    required_permissions = {"read": "employees:read", "write": "employees:write"}


@extend_schema_view(
    partial_update=extend_schema(
        description=(
            "Зміна посади, підрозділу, рівня чи зарплати або звільнення "
            "(date_fired) автоматично додає запис у career-history. "
            "Фото — через multipart/form-data. Зарплата видна лише власнику "
            "і з salary:read; змінити її можна лише з salary:write."
        )
    )
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user", "structural_unit", "position")
    serializer_class = EmployeeSerializer
    permission_classes = [HasPermission]
    required_permissions = {
        "read": "employees:read",
        "write": "employees:write",
        "destroy": "employees:delete",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["structural_unit", "position", "level"]

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "employees:read",
            unit_field="structural_unit",
            owner=Q(user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.user_id == self.request.user.pk

    def perform_create(self, serializer):
        ensure_permission(
            self.request,
            "employees:write",
            serializer.validated_data["structural_unit"],
        )
        serializer.save()

    def perform_update(self, serializer):
        # Переведення: потрібен доступ і до нового підрозділу
        if unit := serializer.validated_data.get("structural_unit"):
            ensure_permission(self.request, "employees:write", unit)
        serializer.save()


@extend_schema_view(
    list=extend_schema(summary="Журнал кадрових подій (тільки читання)")
)
class CareerHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CareerHistory.objects.select_related(
        "employee__user",
        "employee__structural_unit",
        "position",
        "structural_unit",
        "changed_by",
    )
    serializer_class = CareerHistorySerializer
    permission_classes = [HasPermission]
    required_permissions = {"read": "employees:read"}
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "event", "position", "date"]

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "employees:read",
            unit_field="employee__structural_unit",
            owner=Q(employee__user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.employee.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.employee.structural_unit


@extend_schema_view(
    create=extend_schema(summary="Завантажити документ (multipart/form-data)")
)
class EmployeeDocumentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EmployeeDocument.objects.select_related(
        "employee__structural_unit", "uploaded_by"
    )
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [HasPermission]
    required_permissions = {
        "read": "documents:read",
        "write": "documents:write",
        "destroy": "documents:delete",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "document_type"]

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "documents:read",
            unit_field="employee__structural_unit",
            owner=Q(employee__user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.employee.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.employee.structural_unit

    def perform_create(self, serializer):
        employee = serializer.validated_data["employee"]
        ensure_permission(self.request, "documents:write", employee.structural_unit)
        serializer.save(uploaded_by=self.request.user)

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()

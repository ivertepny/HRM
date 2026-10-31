from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

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
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    partial_update=extend_schema(
        description=(
            "Зміна посади, підрозділу, рівня чи зарплати або звільнення "
            "(date_fired) автоматично додає запис у career-history. "
            "Фото — через multipart/form-data."
        )
    )
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user", "structural_unit", "position")
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["structural_unit", "position", "level"]


@extend_schema_view(
    list=extend_schema(summary="Журнал кадрових подій (тільки читання)")
)
class CareerHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CareerHistory.objects.select_related(
        "employee__user", "position", "structural_unit", "changed_by"
    )
    serializer_class = CareerHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "event", "position", "date"]


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
    queryset = EmployeeDocument.objects.select_related("employee", "uploaded_by")
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "document_type"]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CareerHistory, Employee, Position
from .serializers import (
    CareerHistorySerializer,
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


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user", "structural_unit", "position")
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    create=extend_schema(
        summary="Create career history record",
        description="Adds a new career history entry for an employee.",
    )
)
class CareerHistoryViewSet(viewsets.ModelViewSet):
    queryset = CareerHistory.objects.select_related(
        "employee", "position", "structural_unit"
    )
    serializer_class = CareerHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "position", "date"]

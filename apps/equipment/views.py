from django.db.models import OuterRef, Q, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access.permissions import HasPermission, ensure_permission
from apps.access.services import get_access, scope_queryset

from .filters import EquipmentAssignmentFilter, EquipmentFilter
from .models import Equipment, EquipmentAssignment
from .serializers import (
    AssignSerializer,
    EquipmentAssignmentSerializer,
    EquipmentSerializer,
    ReturnSerializer,
    WriteOffSerializer,
)


class EquipmentPermission(HasPermission):
    """Видане обладнання належить підрозділу власника; те, що на складі чи
    списане, — спільне: доступне всім, хто має дозвіл хоч в одному підрозділі."""

    def has_object_permission(self, request, view, obj):
        if obj.holder_id is None:
            codename = self.required_permission(request, view)
            return codename is not None and get_access(request).has_anywhere(codename)
        return super().has_object_permission(request, view, obj)


@extend_schema_view(
    list=extend_schema(
        summary="Обладнання",
        description=(
            "equipment:read — склад, списане і видане працівникам у межах scope; "
            "без дозволу — лише те, що видано вам."
        ),
    ),
    create=extend_schema(summary="Додати обладнання на склад"),
    destroy=extend_schema(
        summary="Видалити обладнання",
        description="Лише без історії видач (помилково внесене); інакше — списання.",
    ),
)
@extend_schema(tags=["Equipment"])
class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.select_related("holder__user")
    serializer_class = EquipmentSerializer
    permission_classes = [EquipmentPermission]
    required_permissions = {
        "read": "equipment:read",
        "write": "equipment:manage",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentFilter

    def get_queryset(self):
        held_since = EquipmentAssignment.objects.filter(
            equipment=OuterRef("pk"), date_returned__isnull=True
        ).values("date_assigned")[:1]
        queryset = super().get_queryset().annotate(held_since=Subquery(held_since))
        owner = Q(holder__user=self.request.user)
        if get_access(self.request).has_anywhere("equipment:read"):
            owner |= Q(holder__isnull=True)
        return scope_queryset(
            self.request,
            queryset,
            "equipment:read",
            unit_field="holder__structural_unit",
            owner=owner,
        )

    def is_owner(self, obj):
        return obj.holder is not None and obj.holder.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.holder.structural_unit if obj.holder else None

    def _respond(self, item):
        return Response(self.get_serializer(self.get_queryset().get(pk=item.pk)).data)

    @extend_schema(
        summary="Видати працівнику",
        description="Потрібен equipment:manage і в підрозділі працівника.",
        request=AssignSerializer,
        responses={200: EquipmentSerializer},
    )
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        item = self.get_object()
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        employee = data["employee_id"]
        ensure_permission(request, "equipment:manage", employee.structural_unit)
        item.assign(employee, data["date"], by=request.user, note=data.get("note", ""))
        return self._respond(item)

    @extend_schema(
        summary="Повернути на склад",
        request=ReturnSerializer,
        responses={200: EquipmentSerializer},
    )
    @action(detail=True, methods=["post"], url_path="return")
    def return_(self, request, pk=None):
        item = self.get_object()
        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item.return_from_holder(
            data["date"], by=request.user, note=data.get("note", "")
        )
        return self._respond(item)

    @extend_schema(
        summary="Списати",
        description="Лише обладнання на складі.",
        request=WriteOffSerializer,
        responses={200: EquipmentSerializer},
    )
    @action(detail=True, methods=["post"], url_path="write-off")
    def write_off(self, request, pk=None):
        item = self.get_object()
        serializer = WriteOffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.write_off(serializer.validated_data["date"])
        return self._respond(item)


@extend_schema_view(
    list=extend_schema(
        summary="Журнал видач",
        description=(
            "Свої — завжди; чужі — з equipment:read (у межах scope). "
            "?active=true — те, що зараз на руках."
        ),
    ),
)
@extend_schema(tags=["Equipment"])
class EquipmentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EquipmentAssignment.objects.select_related(
        "equipment",
        "employee__user",
        "employee__structural_unit",
        "assigned_by",
        "returned_by",
    )
    serializer_class = EquipmentAssignmentSerializer
    permission_classes = [HasPermission]
    required_permissions = {"read": "equipment:read"}
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentAssignmentFilter

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "equipment:read",
            unit_field="employee__structural_unit",
            owner=Q(employee__user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.employee.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.employee.structural_unit

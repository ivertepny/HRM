from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.access.permissions import HasPermission, ensure_permission
from apps.access.services import get_access, scope_queryset
from apps.slack import notify as slack

from .filters import VacationRequestFilter
from .models import VacationRequest
from .serializers import VacationDecisionSerializer, VacationRequestSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Заявки на відпустку",
        description=(
            "Свої — завжди; чужі — з vacations:read (у межах scope). "
            "?date_from / ?date_to — заявки, що перетинаються з періодом."
        ),
    ),
    create=extend_schema(
        summary="Подати заявку",
        description="За себе — vacations:write; за іншого (employee_id) — vacations:manage.",
    ),
)
@extend_schema(tags=["Vacations"])
class VacationRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Заявки не редагуються і не видаляються: лише скасування і розгляд."""

    queryset = VacationRequest.objects.select_related(
        "employee__user", "employee__structural_unit", "created_by", "reviewed_by"
    )
    serializer_class = VacationRequestSerializer
    permission_classes = [HasPermission]
    required_permissions = {
        "read": "vacations:read",
        "create": "vacations:write",
        "cancel": "vacations:write",
        "approve": "vacations:manage",
        "reject": "vacations:manage",
    }
    filter_backends = [DjangoFilterBackend]
    filterset_class = VacationRequestFilter

    def get_queryset(self):
        return scope_queryset(
            self.request,
            super().get_queryset(),
            "vacations:read",
            unit_field="employee__structural_unit",
            owner=Q(employee__user=self.request.user),
        )

    def is_owner(self, obj):
        return obj.employee.user_id == self.request.user.pk

    def get_permission_unit(self, obj):
        return obj.employee.structural_unit

    def perform_create(self, serializer):
        employee = serializer.validated_data["employee"]
        if employee.user_id != self.request.user.pk:
            ensure_permission(
                self.request, "vacations:manage", employee.structural_unit
            )
        vacation = serializer.save(created_by=self.request.user)
        slack.vacation_submitted(vacation, by=self.request.user)

    def _decide(self, request, method):
        vacation = self.get_object()
        serializer = VacationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        getattr(vacation, method)(
            request.user, serializer.validated_data.get("comment", "")
        )
        slack.vacation_decided(vacation)
        return Response(self.get_serializer(vacation).data)

    @extend_schema(
        summary="Схвалити заявку",
        request=VacationDecisionSerializer,
        responses={200: VacationRequestSerializer},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(request, "approve")

    @extend_schema(
        summary="Відхилити заявку",
        request=VacationDecisionSerializer,
        responses={200: VacationRequestSerializer},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, "reject")

    @extend_schema(
        summary="Скасувати заявку",
        description="Власник — поки відпустка не почалась; HR — з vacations:manage.",
        request=None,
        responses={200: VacationRequestSerializer},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        vacation = self.get_object()
        unit = vacation.employee.structural_unit
        if not (
            self.is_owner(vacation) or get_access(request).has("vacations:manage", unit)
        ):
            raise PermissionDenied("Скасувати можна лише власну заявку.")
        vacation.cancel()
        slack.vacation_cancelled(vacation, by=request.user)
        return Response(self.get_serializer(vacation).data)

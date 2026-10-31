from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Permission, Role, UserRole
from .permissions import HasPermission
from .serializers import (
    ESCALATION_MESSAGE,
    PermissionSerializer,
    RoleSerializer,
    UserRoleSerializer,
    missing_permissions,
)
from .services import get_access

ACCESS_PERMISSIONS = {"read": "roles:read", "write": "roles:manage"}


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Каталог дозволів (синхронізується командою seed_roles)."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasPermission]
    required_permissions = ACCESS_PERMISSIONS
    pagination_class = None
    lookup_field = "codename"
    lookup_value_regex = r"[^/]+"


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer
    permission_classes = [HasPermission]
    required_permissions = ACCESS_PERMISSIONS

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Системну роль не можна видалити."})
        codenames = instance.permissions.values_list("codename", flat=True)
        if missing := missing_permissions(self.request, codenames):
            raise PermissionDenied(ESCALATION_MESSAGE.format(", ".join(missing)))
        instance.delete()


class UserRoleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Призначення ролей. Змінити призначення не можна — лише відкликати і видати нове."""

    queryset = UserRole.objects.select_related(
        "user", "role", "structural_unit", "granted_by"
    )
    serializer_class = UserRoleSerializer
    permission_classes = [HasPermission]
    required_permissions = ACCESS_PERMISSIONS
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["user", "role", "structural_unit"]

    def get_permission_unit(self, obj):
        return obj.structural_unit

    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)

    def perform_destroy(self, instance):
        # Відкликати можна лише роль, яку ви змогли б і видати
        codenames = instance.role.permissions.values_list("codename", flat=True)
        missing = missing_permissions(self.request, codenames, instance.structural_unit)
        if missing:
            raise PermissionDenied(ESCALATION_MESSAGE.format(", ".join(missing)))
        instance.delete()


class MyPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Дозволи поточного користувача",
        responses={
            200: inline_serializer(
                name="MyPermissions",
                fields={
                    "is_superuser": serializers.BooleanField(),
                    "global": serializers.ListField(child=serializers.CharField()),
                    "scoped": serializers.ListField(child=serializers.DictField()),
                    "roles": UserRoleSerializer(many=True),
                },
            )
        },
    )
    def get(self, request):
        roles = (
            UserRole.objects.active()
            .filter(user=request.user)
            .select_related("role", "structural_unit", "granted_by", "user")
        )
        return Response(
            {
                **get_access(request).as_dict(),
                "roles": UserRoleSerializer(roles, many=True).data,
            }
        )

from django.utils import timezone
from rest_framework import serializers

from apps.company.models import StructuralUnit

from .models import Permission, Role, UserRole
from .services import get_access

ESCALATION_MESSAGE = "Не можна надавати дозволи, яких немає у вас самих: {}"


def missing_permissions(request, codenames, unit=None):
    access = get_access(request)
    return sorted(c for c in codenames if not access.has(c, unit))


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["codename", "resource", "action", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True, slug_field="codename", queryset=Permission.objects.all()
    )
    users_count = serializers.SerializerMethodField(
        help_text="Користувачі з активним призначенням цієї ролі"
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "permissions",
            "is_system",
            "users_count",
            "created_at",
        ]
        read_only_fields = ["is_system", "created_at"]

    def get_users_count(self, obj) -> int:
        annotated = getattr(obj, "users_count", None)
        if annotated is not None:
            return annotated
        return (
            obj.assignments.active()
            .filter(user__is_active=True)
            .values("user")
            .distinct()
            .count()
        )

    def validate_name(self, value):
        if self.instance and self.instance.is_system and value != self.instance.name:
            raise serializers.ValidationError("Системну роль не можна перейменувати.")
        return value

    def validate_permissions(self, value):
        missing = missing_permissions(
            self.context["request"], [p.codename for p in value]
        )
        if missing:
            raise serializers.ValidationError(
                ESCALATION_MESSAGE.format(", ".join(missing))
            )
        return value


class UserRoleSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    structural_unit_name = serializers.CharField(
        source="structural_unit.name", read_only=True, default=None
    )
    structural_unit = serializers.PrimaryKeyRelatedField(
        queryset=StructuralUnit.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Порожньо — роль діє глобально; інакше — у підрозділі та нащадках",
    )
    granted_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "role_name",
            "structural_unit",
            "structural_unit_name",
            "granted_by",
            "granted_at",
            "expires_at",
        ]
        read_only_fields = ["granted_at"]
        # Унікальність (user, role, unit) з nulls_distinct=False DRF сам не
        # перевіряє — робимо це у validate()
        validators = []

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Дата закінчення має бути в майбутньому.")
        return value

    def validate(self, attrs):
        user, role = attrs["user"], attrs["role"]
        unit = attrs.get("structural_unit")
        if UserRole.objects.filter(user=user, role=role, structural_unit=unit).exists():
            raise serializers.ValidationError(
                "Ця роль уже призначена користувачу в цьому scope."
            )
        codenames = role.permissions.values_list("codename", flat=True)
        missing = missing_permissions(self.context["request"], codenames, unit)
        if missing:
            raise serializers.ValidationError(
                {"role": ESCALATION_MESSAGE.format(", ".join(missing))}
            )
        return attrs

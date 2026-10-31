from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.access.permissions import ensure_permission
from apps.access.services import get_access
from apps.company.models import StructuralUnit
from apps.users.models import User
from apps.users.serializers import UserSerializer

from .models import CareerHistory, Employee, EmployeeDocument, Position

UnitSummaryField = inline_serializer(
    name="UnitSummary",
    fields={"id": serializers.IntegerField(), "full_name": serializers.CharField()},
)


def can_see_salary(request, employee):
    """Власну зарплату видно завжди, чужу — лише з salary:read для підрозділу."""
    if request is None:
        return True
    return employee.user_id == request.user.pk or get_access(request).has(
        "salary:read", employee.structural_unit
    )


class SalaryVisibilityMixin:
    """Прибирає поле salary з відповіді, якщо його не можна бачити."""

    def get_salary_owner(self, instance):
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not can_see_salary(
            self.context.get("request"), self.get_salary_owner(instance)
        ):
            data.pop("salary", None)
        return data


def unit_summary(unit):
    """{'id': 5, 'full_name': 'Company > Department > Team'}"""
    if unit is None:
        return None
    names = [u.name for u in unit.get_ancestors(include_self=True)]
    return {"id": unit.id, "full_name": " > ".join(names)}


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name"]


class EmployeeSerializer(SalaryVisibilityMixin, serializers.ModelSerializer):
    # Поле оголошене вручну, тому DRF не додає перевірку OneToOne сам
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        validators=[
            UniqueValidator(
                queryset=Employee.objects.all(),
                message="Цей користувач уже має профіль працівника.",
            )
        ],
    )
    structural_unit_id = serializers.PrimaryKeyRelatedField(
        queryset=StructuralUnit.objects.filter(is_active=True),
        source="structural_unit",
        write_only=True,
    )
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), source="position", write_only=True
    )

    user = serializers.SerializerMethodField()
    structural_unit = serializers.SerializerMethodField()
    position = PositionSerializer(read_only=True)

    # Не зберігаються в Employee — потрапляють у запис CareerHistory
    change_reason = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=255
    )
    effective_date = serializers.DateField(
        write_only=True,
        required=False,
        help_text="Дата, з якої діє кадрова зміна (за замовчуванням — сьогодні)",
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "user_id",
            "structural_unit",
            "structural_unit_id",
            "position",
            "position_id",
            "level",
            "salary",
            "birth_date",
            "photo",
            "date_hired",
            "date_fired",
            "change_reason",
            "effective_date",
        ]

    @extend_schema_field(UserSerializer)
    def get_user(self, obj):
        return UserSerializer(obj.user).data

    @extend_schema_field(UnitSummaryField)
    def get_structural_unit(self, obj):
        return unit_summary(obj.structural_unit)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        salary_changed = "salary" in attrs and (
            self.instance is None or attrs["salary"] != self.instance.salary
        )
        if request is not None and salary_changed:
            unit = attrs.get("structural_unit") or self.instance.structural_unit
            ensure_permission(request, "salary:write", unit)
        return attrs

    def create(self, validated_data):
        reason, change_date = self._pop_change_meta(validated_data)
        instance = Employee(**validated_data)
        instance._change_reason, instance._change_date = reason, change_date
        instance.save()
        return instance

    def update(self, instance, validated_data):
        instance._change_reason, instance._change_date = self._pop_change_meta(
            validated_data
        )
        return super().update(instance, validated_data)

    @staticmethod
    def _pop_change_meta(validated_data):
        return (
            validated_data.pop("change_reason", ""),
            validated_data.pop("effective_date", None),
        )


class CareerHistorySerializer(SalaryVisibilityMixin, serializers.ModelSerializer):
    """Тільки читання: записи створюються автоматично при зміні Employee."""

    position = PositionSerializer(read_only=True)
    structural_unit = serializers.SerializerMethodField()
    changed_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = CareerHistory
        fields = [
            "id",
            "employee",
            "event",
            "date",
            "position",
            "structural_unit",
            "level",
            "salary",
            "reason",
            "changed_by",
            "created_at",
        ]
        read_only_fields = fields

    def get_salary_owner(self, instance):
        return instance.employee

    @extend_schema_field(UnitSummaryField)
    def get_structural_unit(self, obj):
        return unit_summary(obj.structural_unit)


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = [
            "id",
            "employee",
            "document_type",
            "title",
            "file",
            "uploaded_by",
            "uploaded_at",
        ]
        read_only_fields = ["uploaded_by", "uploaded_at"]

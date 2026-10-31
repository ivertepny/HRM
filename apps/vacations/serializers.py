from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.core.serializers import ModelCleanMixin
from apps.employees.models import Employee

from .models import VacationRequest

EmployeeSummaryField = inline_serializer(
    name="VacationEmployee",
    fields={"id": serializers.IntegerField(), "name": serializers.CharField()},
)


class VacationRequestSerializer(ModelCleanMixin, serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.select_related("user", "structural_unit"),
        source="employee",
        write_only=True,
        required=False,
        help_text="Лише для HR (vacations:manage); без нього — заявка за себе",
    )
    days = serializers.IntegerField(read_only=True)
    created_by = serializers.SlugRelatedField(slug_field="email", read_only=True)
    reviewed_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = VacationRequest
        fields = [
            "id",
            "employee",
            "employee_id",
            "vacation_type",
            "date_start",
            "date_end",
            "days",
            "comment",
            "status",
            "created_by",
            "reviewed_by",
            "reviewed_at",
            "decision_comment",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "reviewed_at",
            "decision_comment",
            "created_at",
        ]

    @extend_schema_field(EmployeeSummaryField)
    def get_employee(self, obj):
        return {"id": obj.employee_id, "name": str(obj.employee)}

    def validate(self, attrs):
        # Працівник потрібен до ModelCleanMixin (перетини, звільнення)
        if "employee" not in attrs:
            employee = getattr(self.context["request"].user, "employee_profile", None)
            if employee is None:
                raise serializers.ValidationError(
                    {"employee_id": "У вас немає профілю працівника."}
                )
            attrs["employee"] = employee
        return super().validate(attrs)


class VacationDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

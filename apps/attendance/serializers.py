from django.utils import timezone
from rest_framework import serializers

from apps.core.serializers import ModelCleanMixin

from .models import AttendanceRecord


class EmployeeSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.CharField(source="__str__")

    class Meta:
        ref_name = "AttendanceEmployee"


class AttendanceRecordSerializer(ModelCleanMixin, serializers.ModelSerializer):
    """Відмітка за день. Подається лише за себе; дата за замовчуванням — сьогодні."""

    employee = EmployeeSummarySerializer(read_only=True)
    date = serializers.DateField(default=timezone.localdate)
    hours = serializers.FloatField(read_only=True, allow_null=True)
    editable = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "employee",
            "date",
            "status",
            "time_start",
            "time_end",
            "hours",
            "comment",
            "editable",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_editable(self, obj) -> bool:
        return obj.is_editable()

    def validate(self, attrs):
        if self.instance is None:
            employee = getattr(self.context["request"].user, "employee_profile", None)
            if employee is None:
                raise serializers.ValidationError(
                    {"date": "У вас немає профілю працівника."}
                )
            attrs["employee"] = employee
            if AttendanceRecord.objects.filter(
                employee=employee, date=attrs["date"]
            ).exists():
                raise serializers.ValidationError(
                    {"date": "За цей день уже є відмітка — відредагуйте її."}
                )
        elif "date" in attrs and attrs["date"] != self.instance.date:
            raise serializers.ValidationError(
                {"date": "Дату відмітки змінити не можна."}
            )
        status = attrs.get("status", getattr(self.instance, "status", None))
        if status == AttendanceRecord.Status.OFF:
            attrs["time_start"] = attrs["time_end"] = None
        return super().validate(attrs)


class ReportRowSerializer(serializers.Serializer):
    employee = EmployeeSummarySerializer()
    unit = serializers.CharField()
    office = serializers.IntegerField()
    remote = serializers.IntegerField()
    off = serializers.IntegerField()
    vacation = serializers.IntegerField(help_text="Робочі дні схваленої відпустки")
    missing = serializers.IntegerField(
        help_text="Робочі дні без відмітки і без відпустки (до сьогодні)"
    )
    hours = serializers.FloatField()


class ReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    working_days = serializers.IntegerField()
    rows = ReportRowSerializer(many=True)

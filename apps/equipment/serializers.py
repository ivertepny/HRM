from django.utils import timezone
from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.employees.models import Employee

from .models import Equipment, EquipmentAssignment


class EmployeeSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.CharField(source="__str__")

    class Meta:
        ref_name = "EquipmentEmployee"


class EquipmentSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField(choices=Equipment.State.choices, read_only=True)
    holder = EmployeeSummarySerializer(read_only=True, allow_null=True)
    held_since = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = Equipment
        fields = [
            "id",
            "name",
            "category",
            "serial_number",
            "description",
            "state",
            "holder",
            "held_since",
            "written_off_at",
            "created_at",
        ]
        read_only_fields = ["written_off_at", "created_at"]

    def to_representation(self, instance):
        # held_since — анотація queryset; після create/assign її немає
        if not hasattr(instance, "held_since"):
            active = instance.assignments.filter(date_returned__isnull=True).first()
            instance.held_since = active.date_assigned if active else None
        return super().to_representation(instance)


class EquipmentAssignmentSerializer(serializers.ModelSerializer):
    equipment = serializers.SerializerMethodField()
    employee = EmployeeSummarySerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    assigned_by = serializers.SlugRelatedField(slug_field="email", read_only=True)
    returned_by = serializers.SlugRelatedField(slug_field="email", read_only=True)

    class Meta:
        model = EquipmentAssignment
        fields = [
            "id",
            "equipment",
            "employee",
            "date_assigned",
            "date_returned",
            "is_active",
            "note",
            "assigned_by",
            "returned_by",
        ]

    @extend_schema_field(
        inline_serializer(
            name="AssignmentEquipment",
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
                "category": serializers.ChoiceField(choices=Equipment.Category.choices),
                "serial_number": serializers.CharField(),
            },
        )
    )
    def get_equipment(self, obj):
        item = obj.equipment
        return {
            "id": item.pk,
            "name": item.name,
            "category": item.category,
            "serial_number": item.serial_number,
        }


class AssignSerializer(serializers.Serializer):
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.select_related("user", "structural_unit")
    )
    date = serializers.DateField(default=timezone.localdate)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ReturnSerializer(serializers.Serializer):
    date = serializers.DateField(default=timezone.localdate)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class WriteOffSerializer(serializers.Serializer):
    date = serializers.DateField(default=timezone.localdate)

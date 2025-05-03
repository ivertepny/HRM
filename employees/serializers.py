from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from company.models import StructuralUnit
from .models import Position, Employee
from users.models import User
from users.serializers import UserSerializer


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name']


class EmployeeSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    structural_unit_id = serializers.PrimaryKeyRelatedField(queryset=StructuralUnit.objects.all(), source='structural_unit', write_only=True)
    position_id = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all(), source='position', write_only=True)

    user = serializers.SerializerMethodField()
    structural_unit = serializers.SerializerMethodField()
    position = PositionSerializer(read_only=True)
    date_hired = serializers.DateField(required=False)
    date_fired = serializers.DateField(required=False)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_id',
            'structural_unit', 'structural_unit_id',
            'position', 'position_id',
            'date_hired', 'date_fired'
        ]

    @extend_schema_field(UserSerializer)
    def get_user(self, obj):
        return UserSerializer(obj.user).data

    def get_structural_unit(self, obj):
        """
        Return dict with full path of structural unit and its ID,
        e.g., {'id': 5, 'full_name': 'Company > Department > Team'}
        """
        unit = obj.structural_unit
        names = []
        current = unit
        while current:
            names.insert(0, current.name)
            current = current.parent
        return {
            'id': unit.id,
            'full_name': ' > '.join(names)
        }

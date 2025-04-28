from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from company.models import StructuralUnit
from .models import Position, Employee, CareerHistory
from users.models import User
from users.serializers import UserSerializer  # Assuming it exists


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name']


class CareerHistorySerializer(serializers.ModelSerializer):
    position = PositionSerializer()

    class Meta:
        model = CareerHistory
        fields = ['id', 'date', 'position', 'salary']


class EmployeeSerializer(serializers.ModelSerializer):
    # Accept user, department, and position IDs during creation
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    structural_unit = serializers.PrimaryKeyRelatedField(queryset=StructuralUnit.objects.all()),
    position_id = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all(), source='position',
                                                     write_only=True)

    # Human-readable output
    user = serializers.SerializerMethodField()
    # structural_unit = serializers.PrimaryKeyRelatedField(queryset=StructuralUnit.objects.all(), source='structural_unit')
    position = PositionSerializer(read_only=True)
    career_history = CareerHistorySerializer(many=True, read_only=True)
    date_hired = serializers.DateField(required=False)
    date_fired = serializers.DateField(required=False)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_id',
            'structural_unit',
            'position', 'position_id',
            'date_hired', 'date_fired', 'career_history'
        ]

    # def get_user(self, obj):
    #     return f"{obj.user.first_name} {obj.user.last_name}"

    @extend_schema_field(UserSerializer)
    def get_user(self, obj):
        return UserSerializer(obj.user).data

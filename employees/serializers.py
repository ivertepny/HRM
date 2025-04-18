from rest_framework import serializers
from .models import Department, Position, Employee, CareerHistory
from users.models import User
from users.serializers import UserSerializer  # Assuming it exists


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


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
    department_id = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), source='department',
                                                       write_only=True)
    position_id = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all(), source='position',
                                                     write_only=True)

    # Human-readable output
    user = serializers.SerializerMethodField()
    department = DepartmentSerializer(read_only=True)
    position = PositionSerializer(read_only=True)
    career_history = CareerHistorySerializer(many=True, read_only=True)
    date_hired = serializers.DateField(required=False)
    date_fired = serializers.DateField(required=False)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_id',
            'department', 'department_id',
            'position', 'position_id',
            'date_hired', 'date_fired', 'career_history'
        ]

    def get_user(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

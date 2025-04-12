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
    user = serializers.SerializerMethodField()
    department = DepartmentSerializer()
    position = PositionSerializer()
    career_history = CareerHistorySerializer(many=True, read_only=True)
    date_hired = serializers.DateField(required=False)
    date_fired = serializers.DateField(required=False)

    class Meta:
        model = Employee
        fields = ['id', 'user', 'department', 'position', 'date_hired', 'date_fired', 'career_history']

    def get_user(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

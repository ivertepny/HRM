from typing import Optional
from django.conf import settings
from rest_framework import serializers
from .models import StructuralUnit
from drf_spectacular.utils import extend_schema_field, inline_serializer


class HistorySerializer(serializers.ModelSerializer):
    history_user = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    event_type = serializers.SerializerMethodField()

    class Meta:
        model = StructuralUnit.history.model
        fields = ['history_date', 'history_user', 'history_type', 'event_type', 'changes', 'ancestors']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_history_user(self, obj) -> Optional[str]:
        return obj.history_user.username if obj.history_user else "Система"

    @extend_schema_field(serializers.ListField())
    def get_changes(self, obj) -> list:
        if obj.prev_record:
            changes = obj.diff_against(obj.prev_record).changes
            return [
                {'field': change.field, 'old': change.old, 'new': change.new}
                for change in changes
            ]
        return []

    @extend_schema_field(serializers.CharField())
    def get_event_type(self, obj) -> str:
        return {
            '+': 'created',
            '~': 'updated',
            '-': 'deleted'
        }.get(obj.history_type, 'unknown')

    @extend_schema_field(
        inline_serializer(
            name='AncestorField',
            fields={
                'id': serializers.IntegerField(),
                'name': serializers.CharField(),
                'type': serializers.CharField()
            },
            many=True
        )
    )
    def get_ancestors(self, obj):
        try:
            current = StructuralUnit.objects.get(id=obj.id)
            ancestors = list(current.get_ancestors()) + [current]
            return [
                {"id": a.id, "name": a.name, "type": a.custom_type}
                for a in ancestors
            ]
        except StructuralUnit.DoesNotExist:
            return []


class StructuralUnitSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=StructuralUnit.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Виберіть ID батьківського підрозділу (дитину, якщо додаєте онука)"
    )
    history = HistorySerializer(many=True, read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    @extend_schema_field(
        inline_serializer(
            name='AncestorField',
            fields={
                'id': serializers.IntegerField(),
                'name': serializers.CharField(),
                'type': serializers.CharField()
            },
            many=True
        )
    )
    def get_ancestors(self, obj):
        current = None

        # Якщо це історичний об’єкт — пробуємо знайти активний
        if hasattr(obj, 'instance') and isinstance(obj.instance, StructuralUnit):
            current = StructuralUnit.objects.filter(id=obj.id).first()
        elif isinstance(obj, StructuralUnit):
            current = obj

        if current:
            return [
                {"id": a.id, "name": a.name, "type": a.custom_type}
                for a in current.get_ancestors()
            ]
        return []

    ancestors = serializers.SerializerMethodField()

    class Meta:
        model = StructuralUnit
        fields = '__all__'
        read_only_fields = ('is_active', 'history', 'lft', 'rght', 'tree_id', 'level')

    def validate_parent(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Не можна додавати до неактивного батька")
        return value

    def validate(self, data):
        """Додаткова валідація для обмеження глибини ієрархії."""
        parent = data.get('parent')
        if parent:
            level = parent.level + 1
            if level > settings.MAX_STRUCTURAL_UNIT_DEPTH:
                raise serializers.ValidationError(
                    f"Максимальна глибина ієрархії: {settings.MAX_STRUCTURAL_UNIT_DEPTH} рівнів")
        return data

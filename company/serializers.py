from rest_framework import serializers
from .models import StructuralUnit
from drf_spectacular.utils import extend_schema_field, inline_serializer


class HistorySerializer(serializers.Serializer):
    history_date = serializers.DateTimeField()
    history_user = serializers.CharField(source='history_user.username')
    changes = serializers.SerializerMethodField()

    def get_changes(self, obj):
        return obj.diff_against(obj.prev_record).changes if obj.prev_record else []


class StructuralUnitSerializer(serializers.ModelSerializer):
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
        return [
            {"id": a.id, "name": a.name, "type": a.custom_type}
            for a in obj.get_ancestors()
        ]

    ancestors = serializers.SerializerMethodField()

    class Meta:
        model = StructuralUnit
        fields = '__all__'
        read_only_fields = ('is_active', 'history', 'lft', 'rght', 'tree_id', 'level')

    def validate_parent(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Не можна додавати до неактивного батька")
        return value

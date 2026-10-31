from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.core.serializers import ModelCleanMixin

from .models import StructuralUnit

# Один компонент на схему: inline_serializer з тим самим name, створений двічі,
# drf-spectacular вважає конфліктом
AncestorField = inline_serializer(
    name="AncestorField",
    fields={
        "id": serializers.IntegerField(),
        "name": serializers.CharField(),
        "type": serializers.CharField(),
    },
    many=True,
)


def ancestors_of(serializer, unit_id, include_self=False):
    """Ланцюжок предків з індексу всіх підрозділів, побудованого один раз на
    відповідь (спільний context серіалізатора) — без запиту на кожен рядок.
    Оргструктура невелика, тож один запит на всі вузли дешевший за N запитів."""
    index = serializer.context.get("_units_index")
    if index is None:
        index = {
            unit_id: (parent_id, name, custom_type)
            for unit_id, parent_id, name, custom_type in StructuralUnit.objects.values_list(
                "id", "parent_id", "name", "custom_type"
            )
        }
        serializer.context["_units_index"] = index

    if unit_id not in index:
        return []
    chain = []
    current = unit_id if include_self else index[unit_id][0]
    while current is not None and current in index:
        parent_id, name, custom_type = index[current]
        chain.append({"id": current, "name": name, "type": custom_type})
        current = parent_id
    return chain[::-1]


class HistorySerializer(serializers.ModelSerializer):
    history_user = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    event_type = serializers.SerializerMethodField()

    class Meta:
        model = StructuralUnit.history.model
        fields = [
            "history_date",
            "history_user",
            "history_type",
            "event_type",
            "changes",
            "ancestors",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_history_user(self, obj) -> str | None:
        return obj.history_user.email if obj.history_user else "Система"

    @extend_schema_field(serializers.ListField())
    def get_changes(self, obj) -> list:
        if obj.prev_record:
            changes = obj.diff_against(obj.prev_record).changes
            return [
                {"field": change.field, "old": change.old, "new": change.new}
                for change in changes
            ]
        return []

    @extend_schema_field(serializers.CharField())
    def get_event_type(self, obj) -> str:
        return {"+": "created", "~": "updated", "-": "deleted"}.get(
            obj.history_type, "unknown"
        )

    @extend_schema_field(AncestorField)
    def get_ancestors(self, obj):
        return ancestors_of(self, obj.id, include_self=True)


class StructuralUnitSerializer(ModelCleanMixin, serializers.ModelSerializer):
    """Підрозділ оргструктури (MPTT-дерево)."""

    parent = serializers.PrimaryKeyRelatedField(
        queryset=StructuralUnit.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Виберіть ID батьківського підрозділу (дитину, якщо додаєте онука)",
    )
    children_count = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()

    @extend_schema_field(serializers.IntegerField())
    def get_children_count(self, obj) -> int:
        # У списках — з анотації get_queryset(); після create/update — запитом
        annotated = getattr(obj, "active_children_count", None)
        if annotated is not None:
            return annotated
        return obj.children.filter(is_active=True).count()

    @extend_schema_field(AncestorField)
    def get_ancestors(self, obj):
        return ancestors_of(self, obj.id)

    class Meta:
        model = StructuralUnit
        fields = "__all__"
        read_only_fields = ("is_active", "lft", "rght", "tree_id", "level")

    def validate_parent(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Не можна додавати до неактивного батька")
        return value

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Equipment, EquipmentAssignment


class AssignmentInline(admin.TabularInline):
    model = EquipmentAssignment
    extra = 0
    can_delete = False
    readonly_fields = (
        "employee",
        "date_assigned",
        "date_returned",
        "note",
        "assigned_by",
        "returned_by",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Equipment)
class EquipmentAdmin(SimpleHistoryAdmin):
    """Видача і повернення — через API (там журнал і перевірки)."""

    list_display = ("name", "category", "serial_number", "holder", "written_off_at")
    list_filter = ("category",)
    search_fields = ("name", "serial_number", "holder__user__last_name")
    readonly_fields = ("holder", "written_off_at", "created_at")
    inlines = [AssignmentInline]

# admin.py
from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import StructuralUnit

@admin.register(StructuralUnit)
class StructuralUnitAdmin(DraggableMPTTAdmin, SimpleHistoryAdmin):
    list_display = ('tree_actions', 'indented_title', 'custom_type', 'is_active')
    list_filter = ('is_active', 'custom_type')
    search_fields = ('name', 'custom_type')
    actions = ['hard_delete']

    def hard_delete(self, request, queryset):
        queryset.delete()
    hard_delete.short_description = "Фізичне видалення (не рекомендується)"

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import VacationRequest


@admin.register(VacationRequest)
class VacationRequestAdmin(SimpleHistoryAdmin):
    list_display = ("employee", "vacation_type", "date_start", "date_end", "status")
    list_filter = ("status", "vacation_type")
    search_fields = ("employee__user__email", "employee__user__last_name")
    date_hierarchy = "date_start"
    readonly_fields = ("created_by", "reviewed_by", "reviewed_at", "created_at")

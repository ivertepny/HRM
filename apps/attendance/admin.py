from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "time_start", "time_end")
    list_filter = ("status",)
    search_fields = ("employee__user__email", "employee__user__last_name")
    date_hierarchy = "date"

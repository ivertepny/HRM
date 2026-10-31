from django.contrib import admin

from .models import AIQuery, ChatSession


class AIQueryInline(admin.TabularInline):
    model = AIQuery
    extra = 0
    fields = ("created_at", "source", "message", "response")
    readonly_fields = fields
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "session_id", "updated_at")
    search_fields = ("name", "user__email")
    readonly_fields = ("session_id", "created_at", "updated_at")
    inlines = [AIQueryInline]

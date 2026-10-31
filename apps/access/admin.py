from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Permission, Role, UserRole


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "description")
    list_filter = ("resource",)
    search_fields = ("codename", "description")

    # Каталог керується командою seed_roles
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "description")
    search_fields = ("name",)
    filter_horizontal = ("permissions",)
    readonly_fields = ("is_system",)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_system)


@admin.register(UserRole)
class UserRoleAdmin(SimpleHistoryAdmin):
    list_display = ("user", "role", "structural_unit", "expires_at", "granted_by")
    list_filter = ("role",)
    search_fields = ("user__email",)
    autocomplete_fields = ("role",)
    readonly_fields = ("granted_by", "granted_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

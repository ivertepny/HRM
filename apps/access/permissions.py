from rest_framework.permissions import SAFE_METHODS, BasePermission

from .services import get_access


class HasPermission(BasePermission):
    """DRF-перевірка дозволів `resource:action` з view.required_permissions.

    required_permissions — словник; ключ шукається в порядку:
    action ViewSet-а ("list", "approve", ...) → HTTP-метод ("GET") →
    "read" для безпечних методів / "write" для решти → "*".

        required_permissions = {"read": "roles:read", "write": "roles:manage"}

    Якщо для запиту дозвіл не знайдено — доступ заборонено (secure by default).
    На рівні об'єкта перевіряється scope: підрозділ береться з
    view.get_permission_unit(obj) або obj.structural_unit.
    """

    message = "Недостатньо прав для цієї дії."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        codename = self.required_permission(request, view)
        return codename is not None and get_access(request).has_anywhere(codename)

    def has_object_permission(self, request, view, obj):
        codename = self.required_permission(request, view)
        if codename is None:
            return False
        if hasattr(view, "get_permission_unit"):
            unit = view.get_permission_unit(obj)
        else:
            unit = getattr(obj, "structural_unit", None)
        return get_access(request).has(codename, unit)

    @staticmethod
    def required_permission(request, view):
        required = getattr(view, "required_permissions", {})
        keys = (
            getattr(view, "action", None),
            request.method,
            "read" if request.method in SAFE_METHODS else "write",
            "*",
        )
        return next((required[key] for key in keys if key in required), None)

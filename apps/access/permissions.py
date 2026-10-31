from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .services import get_access


def ensure_permission(request, codename, unit=None):
    """Для перевірок, яких не видно з URL: цільовий підрозділ при створенні
    чи переведенні, окремий дозвіл на поле (salary) тощо."""
    if not get_access(request).has(codename, unit):
        scope = f" у підрозділі «{unit.name}»" if unit is not None else ""
        raise PermissionDenied(f"Потрібен дозвіл {codename}{scope}.")


class HasPermission(BasePermission):
    """DRF-перевірка дозволів `resource:action` з view.required_permissions.

    required_permissions — словник; ключ шукається в порядку:
    action ViewSet-а ("list", "approve", ...) → HTTP-метод ("GET") →
    "read" для безпечних методів / "write" для решти → "*".

        required_permissions = {"read": "roles:read", "write": "roles:manage"}

    Якщо для запиту дозвіл не знайдено — доступ заборонено (secure by default).
    На рівні об'єкта перевіряється scope: підрозділ береться з
    view.get_permission_unit(obj) або obj.structural_unit.

    Власні дані: якщо view визначає is_owner(obj), власник завжди може
    виконувати над своїм об'єктом методи з view.owner_methods (за
    замовчуванням — лише читання) без дозволу. Тоді list дозволений
    будь-кому, а view зобов'язаний звузити queryset через
    scope_queryset(..., owner=...).
    """

    message = "Недостатньо прав для цієї дії."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if not hasattr(view, request.method.lower()):
            # Метод не підтримується view — хай DRF відповість 405, а не 403
            return True
        codename = self.required_permission(request, view)
        if codename is None:
            return False
        if get_access(request).has_anywhere(codename):
            return True
        return self._owner_allowed(request, view)

    def has_object_permission(self, request, view, obj):
        codename = self.required_permission(request, view)
        if codename is None:
            return False
        if self._owner_allowed(request, view) and view.is_owner(obj):
            return True
        return get_access(request).has(codename, self.permission_unit(view, obj))

    @staticmethod
    def _owner_allowed(request, view):
        if not hasattr(view, "is_owner"):
            return False
        return request.method in getattr(view, "owner_methods", SAFE_METHODS)

    @staticmethod
    def permission_unit(view, obj):
        if hasattr(view, "get_permission_unit"):
            return view.get_permission_unit(obj)
        return getattr(obj, "structural_unit", None)

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

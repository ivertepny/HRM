"""Обчислення прав користувача.

UserAccess завантажує всі активні призначення ролей одним запитом і далі
відповідає на питання "чи можна" без звернень до БД. Для HTTP-запиту
використовуйте get_access(request) — результат кешується на час запиту.
"""

from django.db.models import Q

from apps.company.models import StructuralUnit

from .catalog import WILDCARD, matches
from .models import UserRole

_REQUEST_CACHE_ATTR = "_user_access"


class UserAccess:
    def __init__(self, user):
        self.user = user
        self.is_superuser = bool(user and user.is_authenticated and user.is_superuser)
        self.global_permissions = set()
        # unit_id -> дозволи з ролей, призначених на цей підрозділ
        self.scoped_permissions = {}
        if user and user.is_authenticated and user.is_active and not self.is_superuser:
            self._load()

    def _load(self):
        assignments = (
            UserRole.objects.active()
            .filter(user=self.user, role__permissions__isnull=False)
            .values_list("structural_unit_id", "role__permissions__codename")
        )
        for unit_id, codename in assignments:
            if unit_id is None:
                self.global_permissions.add(codename)
            else:
                self.scoped_permissions.setdefault(unit_id, set()).add(codename)

    def has(self, codename, unit=None):
        """Дозвіл глобально або (якщо задано unit) через роль на unit чи його предка."""
        if self.is_superuser or matches(self.global_permissions, codename):
            return True
        if unit is None or not self.scoped_permissions:
            return False
        ancestor_ids = unit.get_ancestors(include_self=True).values_list(
            "id", flat=True
        )
        return any(
            matches(self.scoped_permissions.get(unit_id, ()), codename)
            for unit_id in ancestor_ids
        )

    def has_anywhere(self, codename):
        """Дозвіл глобально або хоча б в одному підрозділі (для list/create)."""
        return self.has(codename) or any(
            matches(perms, codename) for perms in self.scoped_permissions.values()
        )

    def units_for(self, codename):
        """Підрозділи, де діє дозвіл: None — без обмежень, інакше queryset.

        Для фільтрації списків: queryset.filter(structural_unit__in=...).
        """
        if self.has(codename):
            return None
        roots = [
            unit_id
            for unit_id, perms in self.scoped_permissions.items()
            if matches(perms, codename)
        ]
        if not roots:
            return StructuralUnit.objects.none()
        subtree = Q()
        for root in StructuralUnit.objects.filter(id__in=roots):
            subtree |= Q(tree_id=root.tree_id, lft__gte=root.lft, rght__lte=root.rght)
        return StructuralUnit.objects.filter(subtree)

    def covers(self, codenames, unit=None):
        """Чи має користувач усі дозволи — для захисту від ескалації прав."""
        return all(self.has(c, unit) for c in codenames)

    def as_dict(self):
        if self.is_superuser:
            return {
                "is_superuser": True,
                "global": [f"{WILDCARD}:{WILDCARD}"],
                "scoped": [],
            }
        units = StructuralUnit.objects.in_bulk(self.scoped_permissions.keys())
        return {
            "is_superuser": False,
            "global": sorted(self.global_permissions),
            "scoped": [
                {
                    "unit": {"id": unit_id, "name": units[unit_id].name},
                    "permissions": sorted(perms),
                }
                for unit_id, perms in sorted(self.scoped_permissions.items())
                if unit_id in units
            ],
        }


def get_access(request):
    access = getattr(request, _REQUEST_CACHE_ATTR, None)
    if access is None or access.user != request.user:
        access = UserAccess(request.user)
        setattr(request, _REQUEST_CACHE_ATTR, access)
    return access

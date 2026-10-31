"""Обчислення прав користувача.

UserAccess завантажує всі активні призначення ролей одним запитом і далі
відповідає на питання "чи можна" без звернень до БД. Результат кешується
між запитами (apps.access.cache, Redis) і на час HTTP-запиту
(get_access(request)).
"""

from django.conf import settings
from django.db.models import Min, Q
from django.utils import timezone

from apps.company.models import StructuralUnit

from . import cache as access_cache
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
        key = access_cache.key_for(self.user.pk)
        cached = access_cache.load(key)
        if cached is None:
            cached, timeout = self._query()
            access_cache.store(key, cached, timeout)
        self.global_permissions, self.scoped_permissions = cached

    def _query(self):
        """(global, scoped) з БД і TTL для кешу: не довше, ніж до закінчення
        найближчої тимчасової ролі."""
        active = UserRole.objects.active().filter(user=self.user)
        global_permissions, scoped_permissions = set(), {}
        assignments = active.filter(role__permissions__isnull=False).values_list(
            "structural_unit_id", "role__permissions__codename"
        )
        for unit_id, codename in assignments:
            if unit_id is None:
                global_permissions.add(codename)
            else:
                scoped_permissions.setdefault(unit_id, set()).add(codename)

        timeout = settings.ACCESS_CACHE_TIMEOUT
        next_expiry = active.aggregate(next=Min("expires_at"))["next"]
        if next_expiry is not None:
            seconds_left = int((next_expiry - timezone.now()).total_seconds())
            timeout = min(timeout, seconds_left)
        return (global_permissions, scoped_permissions), timeout

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


def scope_queryset(request, queryset, codename, unit_field=None, owner=None):
    """Звужує queryset до того, що користувач може бачити за `codename`.

    unit_field — шлях до StructuralUnit (напр. "employee__structural_unit");
    без нього scoped-ролі нічого не відкривають (ресурс лише глобальний).
    owner — Q-умова "власні записи", які видно завжди.
    """
    access = get_access(request)
    units = access.units_for(codename)
    if units is None:
        return queryset
    condition = Q(pk__in=[])
    if unit_field and access.scoped_permissions:
        condition |= Q(**{f"{unit_field}__in": units})
    if owner is not None:
        condition |= owner
    return queryset.filter(condition)


def grant_default_role(user, granted_by=None):
    """Видає новому користувачу базову роль (якщо seed_roles уже виконано)."""
    from .catalog import DEFAULT_ROLE
    from .models import Role

    role = Role.objects.filter(name=DEFAULT_ROLE).first()
    if role is None:
        return None
    assignment, _ = UserRole.objects.get_or_create(
        user=user, role=role, structural_unit=None, defaults={"granted_by": granted_by}
    )
    return assignment


def get_access(request):
    access = getattr(request, _REQUEST_CACHE_ATTR, None)
    if access is None or access.user != request.user:
        access = UserAccess(request.user)
        setattr(request, _REQUEST_CACHE_ATTR, access)
    return access

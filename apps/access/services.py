"""Обчислення прав користувача.

UserAccess завантажує всі активні призначення ролей одним запитом і далі
відповідає на питання "чи можна" без звернень до БД. Результат кешується
між запитами (apps.access.cache, Redis) і на час HTTP-запиту
(get_access(request)).
"""

from functools import cached_property

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
        # Без запитів: unit у піддереві кореня, якщо його MPTT-інтервал
        # вкладений в інтервал кореня (важливо для перевірок у списках)
        return any(
            tree_id == unit.tree_id and lft <= unit.lft and unit.rght <= rght
            for tree_id, lft, rght in self._scope_roots(codename)
        )

    @cached_property
    def _root_bounds(self):
        """unit_id -> (tree_id, lft, rght) підрозділів зі scoped-ролями; один запит."""
        return {
            unit_id: (tree_id, lft, rght)
            for unit_id, tree_id, lft, rght in StructuralUnit.objects.filter(
                id__in=self.scoped_permissions
            ).values_list("id", "tree_id", "lft", "rght")
        }

    def _scope_roots(self, codename):
        """MPTT-межі підрозділів, на які видано роль з цим дозволом."""
        return [
            self._root_bounds[unit_id]
            for unit_id, perms in self.scoped_permissions.items()
            if unit_id in self._root_bounds and matches(perms, codename)
        ]

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
        roots = self._scope_roots(codename)
        if not roots:
            return StructuralUnit.objects.none()
        subtree = Q()
        for tree_id, lft, rght in roots:
            subtree |= Q(tree_id=tree_id, lft__gte=lft, rght__lte=rght)
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
    return scope_for_access(get_access(request), queryset, codename, unit_field, owner)


def scope_for_access(access, queryset, codename, unit_field=None, owner=None):
    """Те саме, що scope_queryset, але для UserAccess поза HTTP-запитом
    (management-команди, нагадування)."""
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


def users_with_permission(codename, unit=None, anywhere=False):
    """Активні користувачі, яким роль дає `codename` глобально або (з unit) —
    на цей підрозділ чи його предка; anywhere=True — будь-яке призначення,
    зокрема лише на якийсь підрозділ. Для сповіщень: кому слати заявку на
    розгляд. Суперкористувачі без ролей сюди не входять — їм не пишемо."""
    from apps.users.models import User

    resource = codename.split(":")[0]
    granted = [codename, f"{resource}:{WILDCARD}", f"{WILDCARD}:{WILDCARD}"]
    where = Q(structural_unit__isnull=True)
    if unit is not None:
        where |= Q(structural_unit__in=unit.get_ancestors(include_self=True))
    assignments = UserRole.objects.active().filter(
        role__permissions__codename__in=granted
    )
    if not anywhere:
        assignments = assignments.filter(where)
    return User.objects.filter(
        is_active=True, pk__in=assignments.values("user_id")
    ).order_by("pk")


def get_access(request):
    access = getattr(request, _REQUEST_CACHE_ATTR, None)
    if access is None or access.user != request.user:
        access = UserAccess(request.user)
        setattr(request, _REQUEST_CACHE_ATTR, access)
    return access

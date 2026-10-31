"""Інвалідація кешу прав (apps.access.cache) при зміні ролей і дозволів.

Інвалідуємо одразу і ще раз після коміту: перше прибирає застарілі дані
для цієї ж транзакції, друге — для запитів, які встигли перерахувати права
до коміту.
"""

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from . import cache as access_cache
from .models import Permission, Role, UserRole


def _now_and_on_commit(func, *args):
    func(*args)
    transaction.on_commit(lambda: func(*args))


@receiver([post_save, post_delete], sender=UserRole)
def user_role_changed(sender, instance, **kwargs):
    _now_and_on_commit(access_cache.invalidate_user, instance.user_id)


@receiver(m2m_changed, sender=Role.permissions.through)
def role_permissions_changed(sender, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _now_and_on_commit(access_cache.invalidate_all)


@receiver(post_delete, sender=Role)
@receiver([post_save, post_delete], sender=Permission)
def catalog_changed(sender, **kwargs):
    _now_and_on_commit(access_cache.invalidate_all)

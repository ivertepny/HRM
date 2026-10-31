from django.core.management.base import BaseCommand
from django.db import transaction

from apps.access.catalog import SYSTEM_ROLES, all_codenames, describe
from apps.access.models import Permission, Role


class Command(BaseCommand):
    help = (
        "Синхронізує каталог дозволів з apps/access/catalog.py і створює "
        "системні ролі. Безпечно запускати повторно."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-system-roles",
            action="store_true",
            help="Перезаписати дозволи наявних системних ролей значеннями з каталогу",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Видалити дозволи, яких більше немає в каталозі",
        )

    @transaction.atomic
    def handle(self, *args, reset_system_roles=False, prune=False, **options):
        codenames = all_codenames()
        created = 0
        for codename in codenames:
            resource, action = codename.split(":")
            _, was_created = Permission.objects.update_or_create(
                resource=resource,
                action=action,
                defaults={"description": describe(codename)},
            )
            created += was_created
        self.stdout.write(f"Дозволи: {len(codenames)} у каталозі, нових {created}")

        stale = Permission.objects.exclude(codename__in=codenames)
        if stale.exists():
            names = ", ".join(stale.values_list("codename", flat=True))
            if prune:
                stale.delete()
                self.stdout.write(self.style.WARNING(f"Видалено застарілі: {names}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Застарілі (не видалено, див. --prune): {names}"
                    )
                )

        for name, spec in SYSTEM_ROLES.items():
            role, was_created = Role.objects.get_or_create(
                name=name, defaults={"description": spec["description"]}
            )
            if not role.is_system:
                role.is_system = True
                role.save(update_fields=["is_system"])
            if was_created or reset_system_roles:
                role.permissions.set(
                    Permission.objects.filter(codename__in=spec["permissions"])
                )
                status = "створено" if was_created else "оновлено"
            else:
                status = "без змін"
            self.stdout.write(f"Роль «{name}»: {status}")

        self.stdout.write(self.style.SUCCESS("Готово."))

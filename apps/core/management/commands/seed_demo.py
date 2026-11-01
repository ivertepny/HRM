"""Демо-дані для локальної розробки та e2e-тестів. Ідемпотентна."""

import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.access.models import Role, UserRole
from apps.access.services import grant_default_role
from apps.attendance.models import AttendanceRecord
from apps.company.models import StructuralUnit
from apps.employees.models import Employee, Position
from apps.equipment.models import Equipment
from apps.users.models import User
from apps.vacations.models import VacationRequest

DEFAULT_PASSWORD = "Demo-pass-2026"

# email, ім'я, прізвище, підрозділ, посада, рівень, зарплата, додаткова роль
PEOPLE = [
    (
        "admin@example.com",
        "Адміністратор",
        "Системи",
        None,
        None,
        "",
        None,
        "System Admin",
    ),
    (
        "hr@example.com",
        "Ганна",
        "Мельник",
        "HR",
        "HR-менеджерка",
        "",
        "52000.00",
        "HR Manager",
    ),
    (
        "olena@example.com",
        "Олена",
        "Коваль",
        "IT",
        "Розробниця",
        "middle",
        "68000.00",
        None,
    ),
    (
        "petro@example.com",
        "Петро",
        "Шевчук",
        "Backend",
        "Розробник",
        "senior",
        "92000.00",
        None,
    ),
    (
        "maria@example.com",
        "Марія",
        "Бондар",
        "Frontend",
        "Розробниця",
        "junior",
        "41000.00",
        None,
    ),
]


class Command(BaseCommand):
    help = "Створює демо-структуру, користувачів і заявки (лише для розробки та e2e)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Пароль для всіх демо-користувачів",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Дозволити запуск при DEBUG=False (не для продакшну!)",
        )

    @transaction.atomic
    def handle(self, *args, password, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError(
                "seed_demo — лише для розробки (DEBUG=False). Див. --force."
            )

        call_command("seed_roles", verbosity=0)
        units = self._units()

        employees = {}
        for email, first, last, unit, position, level, salary, role in PEOPLE:
            user, created = User.objects.get_or_create(
                email=email, defaults={"first_name": first, "last_name": last}
            )
            if created:
                user.set_password(password)
                user.save()
            grant_default_role(user)
            if role:
                UserRole.objects.get_or_create(
                    user=user, role=Role.objects.get(name=role), structural_unit=None
                )
            if unit:
                employees[email], _ = Employee.objects.get_or_create(
                    user=user,
                    defaults={
                        "structural_unit": units[unit],
                        "position": Position.objects.get_or_create(name=position)[0],
                        "level": level,
                        "salary": salary,
                        "date_hired": datetime.date(2024, 3, 1),
                    },
                )

        self._vacations(employees)
        self._equipment(employees)
        self._attendance(employees)
        self.stdout.write(
            self.style.SUCCESS(
                f"Демо-дані готові. Користувачі: {', '.join(p[0] for p in PEOPLE)}; "
                "пароль — значення --password."
            )
        )

    def _units(self):
        def unit(name, unit_type, parent=None):
            obj, _ = StructuralUnit.objects.get_or_create(
                name=name, parent=parent, defaults={"custom_type": unit_type}
            )
            return obj

        hq = unit("Головний офіс", "Офіс")
        it = unit("IT", "Департамент", hq)
        return {
            "HR": unit("HR", "Відділ", hq),
            "IT": it,
            "Backend": unit("Backend", "Команда", it),
            "Frontend": unit("Frontend", "Команда", it),
            "Продажі": unit("Продажі", "Департамент", hq),
        }

    def _vacations(self, employees):
        today = timezone.localdate()
        start = today + datetime.timedelta(days=14)
        VacationRequest.objects.get_or_create(
            employee=employees["petro@example.com"],
            date_start=start,
            defaults={
                "date_end": start + datetime.timedelta(days=4),
                "comment": "Поїздка до батьків",
            },
        )
        approved_start = today + datetime.timedelta(days=30)
        VacationRequest.objects.get_or_create(
            employee=employees["maria@example.com"],
            date_start=approved_start,
            defaults={
                "date_end": approved_start + datetime.timedelta(days=6),
                "status": VacationRequest.Status.APPROVED,
            },
        )

    def _equipment(self, employees):
        """Ноутбуки в розробників, монітор і ноутбук на складі, списаний телефон."""
        laptop = Equipment.Category.LAPTOP
        items = [
            ("Lenovo ThinkPad T14", laptop, "DEMO-LT-001", "olena@example.com"),
            ("Apple MacBook Pro 14", laptop, "DEMO-LT-002", "petro@example.com"),
            ("Dell Latitude 5440", laptop, "DEMO-LT-003", "maria@example.com"),
            ("Dell Latitude 5440", laptop, "DEMO-LT-004", None),
            ('Dell P2723DE 27"', Equipment.Category.MONITOR, "DEMO-MN-001", None),
        ]
        hired = datetime.date(2024, 3, 1)
        for name, category, serial, holder in items:
            item, created = Equipment.objects.get_or_create(
                serial_number=serial, defaults={"name": name, "category": category}
            )
            if created and holder:
                item.assign(employees[holder], hired)

        phone, created = Equipment.objects.get_or_create(
            serial_number="DEMO-PH-001",
            defaults={
                "name": "Samsung Galaxy A54",
                "category": Equipment.Category.PHONE,
            },
        )
        if created:
            phone.write_off(datetime.date(2025, 6, 1))

    def _attendance(self, employees):
        """Табель за попередні 5 робочих днів (сьогодні — без відмітки)."""
        statuses = {
            "olena@example.com": ["office", "office", "remote", "office", "remote"],
            "petro@example.com": ["remote", "remote", "office", "remote", "off"],
            "maria@example.com": ["office", "office", "office", "remote", "office"],
        }
        days, day = [], timezone.localdate()
        while len(days) < 5:
            day -= datetime.timedelta(days=1)
            if day.weekday() < 5:
                days.append(day)
        for email, plan in statuses.items():
            for date, status in zip(days, plan, strict=True):
                times = (
                    {}
                    if status == "off"
                    else {"time_start": datetime.time(9), "time_end": datetime.time(18)}
                )
                AttendanceRecord.objects.get_or_create(
                    employee=employees[email],
                    date=date,
                    defaults={"status": status, **times},
                )

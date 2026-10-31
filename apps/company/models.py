# company/models.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords


class StructuralUnit(MPTTModel):
    name = models.CharField(max_length=100)
    custom_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Тип підрозділу (наприклад: 'Офіс', 'Департамент')",
    )
    parent = TreeForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords(
        excluded_fields=["lft", "rght", "tree_id", "level"], inherit=True
    )

    class MPTTMeta:
        db_table = "company_structuralunit"
        order_insertion_by = ["name"]

    def clean(self):
        super().clean()

        # Унікальність імені серед активних підрозділів одного рівня (і серед коренів)
        siblings = StructuralUnit.objects.filter(
            parent=self.parent, name=self.name, is_active=True
        )
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)
        if siblings.exists():
            raise ValidationError(
                {"name": f"Підрозділ з ім'ям '{self.name}' вже існує на цьому рівні"}
            )

        if self.parent is None:
            return

        # Перевірка на циклічність: не можна стати дитиною себе чи свого нащадка
        if self.pk and (
            self.parent.pk == self.pk
            or self.get_descendants().filter(pk=self.parent.pk).exists()
        ):
            raise ValidationError({"parent": "Спроба створити циклічний зв'язок"})

        # Обмеження глибини ієрархії — рахуємо від нового батька
        if self.parent.get_level() + 1 > settings.MAX_STRUCTURAL_UNIT_DEPTH:
            raise ValidationError(
                {
                    "parent": f"Максимальна глибина ієрархії: "
                    f"{settings.MAX_STRUCTURAL_UNIT_DEPTH} рівнів"
                }
            )

    def delete(self, *args, **kwargs):
        """Soft delete з каскадуванням"""
        self.is_active = False
        self.save()
        self.get_descendants().update(is_active=False)

    def get_lowest_level_descendants(self):
        """
        Повертає всі нащадки, які є на найнижчому рівні в ієрархії.
        """
        return self.get_descendants().filter(level=self.get_level() + 1)

    def __str__(self):
        return f"{self.custom_type}: {self.name}" if self.custom_type else self.name

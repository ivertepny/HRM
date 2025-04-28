# models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords


class StructuralUnit(MPTTModel):
    name = models.CharField(max_length=100)
    custom_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Тип підрозділу (наприклад: 'Офіс', 'Департамент')"
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords(
        excluded_fields=['lft', 'rght', 'tree_id', 'level'],
        inherit=True
    )

    class MPTTMeta:
        db_table = 'company_structuralunit'
        order_insertion_by = ['name']

    def clean(self):
        super().clean()

        # Унікальність імені серед дітей одного батька
        if self.parent:
            siblings = self.parent.children.exclude(id=self.id) if self.id else self.parent.children.all()
            if siblings.filter(name=self.name, is_active=True).exists():
                raise ValidationError(
                    {'name': f"Підрозділ з ім'ям '{self.name}' вже існує у цього батька"}
                )

        # Перевірка на циклічність
        if self.parent and self.parent in self.get_descendants():
            raise ValidationError("Спроба створити циклічний зв'язок")

        # Обмеження глибини ієрархії
        if self.get_level() > settings.MAX_STRUCTURAL_UNIT_DEPTH:
            raise ValidationError(f"Максимальна глибина ієрархії: {settings.MAX_STRUCTURAL_UNIT_DEPTH} рівнів")

    def delete(self, *args, **kwargs):
        """Soft delete з каскадуванням"""
        self.is_active = False
        self.save()
        self.get_descendants().update(is_active=False)

    def __str__(self):
        return f"{self.custom_type}: {self.name}" if self.custom_type else self.name

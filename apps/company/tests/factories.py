import factory

from apps.company.models import StructuralUnit


class StructuralUnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StructuralUnit

    name = factory.Sequence(lambda n: f"Unit {n}")
    custom_type = "Департамент"
    parent = None

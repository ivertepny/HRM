import factory

from apps.equipment.models import Equipment


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    name = factory.Sequence(lambda n: f"ThinkPad T14 #{n}")
    category = Equipment.Category.LAPTOP
    serial_number = factory.Sequence(lambda n: f"SN-{n:06d}")

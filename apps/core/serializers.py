import copy


class ModelCleanMixin:
    """Викликає Model.clean() під час валідації ModelSerializer.

    DRF, на відміну від Django-форм, не викликає clean(), тому бізнес-правила
    з моделі через API не перевіряються. Міксин застосовує нові значення до
    копії об'єкта і викликає clean(); DjangoValidationError DRF сам перетворює
    на 400 з помилками по полях.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        model = self.Meta.model
        instance = copy.copy(self.instance) if self.instance else model()
        m2m = {f.name for f in model._meta.many_to_many}
        for name, value in attrs.items():
            if name not in m2m:
                setattr(instance, name, value)
        instance.clean()
        return attrs

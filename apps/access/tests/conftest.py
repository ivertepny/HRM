import pytest


@pytest.fixture(autouse=True)
def _seeded(catalog):
    """Тести access завжди працюють з засіяним каталогом."""

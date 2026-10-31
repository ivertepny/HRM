from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_size(file):
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(
            f"Файл завеликий: максимум {settings.MAX_UPLOAD_SIZE_MB} МБ."
        )

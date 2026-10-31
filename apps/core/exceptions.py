"""Глобальний обробник помилок DRF (REST_FRAMEWORK["EXCEPTION_HANDLER"]).

Перетворює помилки Django/БД на коректні HTTP-відповіді, щоб views не ловили
їх вручну. Все, що не оброблено тут, — справжній баг: DRF віддає 500 без деталей
(у DEBUG — з traceback).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError, RestrictedError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))
    elif isinstance(exc, ProtectedError | RestrictedError):
        return Response(
            {
                "detail": "Об'єкт використовується іншими записами і не може бути видалений."
            },
            status=status.HTTP_409_CONFLICT,
        )
    elif isinstance(exc, IntegrityError):
        return Response(
            {"detail": "Конфлікт даних: порушено обмеження цілісності."},
            status=status.HTTP_409_CONFLICT,
        )
    return drf_exception_handler(exc, context)

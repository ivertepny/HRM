"""Глобальний обробник помилок DRF (REST_FRAMEWORK["EXCEPTION_HANDLER"]).

Перетворює помилки Django/БД на коректні HTTP-відповіді, щоб views не ловили
їх вручну. Все, що не оброблено тут, — справжній баг: DRF віддає 500 без деталей
(у DEBUG — з traceback).
"""

import math

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
    elif isinstance(exc, exceptions.Throttled):
        # У DRF переклад неповний («… Expected available in N seconds.»)
        # Без wait у конструкторі (він дописав би англійський хвіст); wait потрібен
        # обробнику DRF для заголовка Retry-After
        wait = exc.wait
        exc = exceptions.Throttled(detail=throttled_message(wait))
        exc.wait = wait
    return drf_exception_handler(exc, context)


def throttled_message(wait):
    if wait is None:
        return "Забагато запитів. Спробуйте пізніше."
    minutes = math.ceil(wait / 60)
    if minutes <= 1:
        return "Забагато запитів. Спробуйте за хвилину."
    return f"Забагато запитів. Спробуйте за {minutes} хв."


class ServiceUnavailable(exceptions.APIException):
    """Зовнішній сервіс (OpenAI, email тощо) недоступний — 503, а не 500."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Сервіс тимчасово недоступний. Спробуйте пізніше."
    default_code = "service_unavailable"

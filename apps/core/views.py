import mimetypes

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Q
from django.http import FileResponse, Http404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.services import scope_queryset
from apps.employees.models import Employee, EmployeeDocument


class HealthView(APIView):
    """Для healthcheck контейнера і зовнішнього моніторингу: БД і кеш живі."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health"],
        summary="Стан сервісу",
        responses={
            200: inline_serializer("Health", {"status": serializers.CharField()}),
            503: inline_serializer("HealthError", {"status": serializers.CharField()}),
        },
    )
    def get(self, request):
        try:
            connection.ensure_connection()
            cache.set("health", "ok", 5)
            if cache.get("health") != "ok":
                raise RuntimeError("cache")
        except Exception:
            return Response(
                {"status": "error"}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response({"status": "ok"})


@extend_schema(exclude=True)
class MediaView(APIView):
    """Завантажені файли — лише тим, хто бачить їхнього власника.

    Фото — з областю employees:read, документи — documents:read (свої — завжди).
    Файли без запису в БД (сироти, чужі шляхи) — 404, як і недоступні.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, path):
        if not (self._allowed(request, path) and default_storage.exists(path)):
            raise Http404
        content_type, _ = mimetypes.guess_type(path)
        response = FileResponse(
            default_storage.open(path),
            content_type=content_type or "application/octet-stream",
        )
        # Доступ залежить від користувача — спільні кеші не зберігають
        response["Cache-Control"] = "private, no-store"
        return response

    @staticmethod
    def _allowed(request, path):
        user = request.user
        if path.startswith("employees/photos/"):
            return scope_queryset(
                request,
                Employee.objects.filter(photo=path),
                "employees:read",
                unit_field="structural_unit",
                owner=Q(user=user),
            ).exists()
        if path.startswith("employees/"):
            return scope_queryset(
                request,
                EmployeeDocument.objects.filter(file=path),
                "documents:read",
                unit_field="employee__structural_unit",
                owner=Q(employee__user=user),
            ).exists()
        return False

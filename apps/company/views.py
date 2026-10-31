from django.db.models import Count, Q
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from graphviz import Digraph
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.access.permissions import HasPermission, ensure_permission
from apps.access.services import scope_queryset

from .models import StructuralUnit
from .serializers import HistorySerializer, StructuralUnitSerializer


class StructuralUnitViewSet(viewsets.ModelViewSet):
    serializer_class = StructuralUnitSerializer
    queryset = StructuralUnit.objects.filter(is_active=True)
    permission_classes = [HasPermission]
    required_permissions = {
        "read": "company:read",
        "write": "company:write",
        "destroy": "company:delete",
    }

    def get_queryset(self):
        # Scoped-роль бачить свій підрозділ і його нащадків
        queryset = scope_queryset(
            self.request, super().get_queryset(), "company:read", unit_field="pk"
        )
        if unit_type := self.request.query_params.get("type"):
            queryset = queryset.filter(custom_type=unit_type)
        # GROUP BY скидає Meta.ordering MPTT — порядок дерева задаємо явно
        return queryset.annotate(
            active_children_count=Count("children", filter=Q(children__is_active=True))
        ).order_by("tree_id", "lft")

    @extend_schema(
        summary="Отримати історію змін",
        responses={200: HistorySerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                description="Кількість останніх записів",
                required=False,
            )
        ],
    )
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        unit = self.get_object()
        history = unit.history.all().order_by("-history_date")
        if limit := request.query_params.get("limit"):
            if not limit.isdigit():
                raise ValidationError({"limit": "Має бути додатним цілим числом."})
            history = history[: int(limit)]
        serializer = HistorySerializer(history, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Згенерувати діаграму", responses={200: OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def diagram(self, request, pk=None):
        unit = self.get_object()
        graph = Digraph(format="svg", graph_attr={"rankdir": "TB"})

        def add_nodes(node):
            color = "lightgrey" if not node.is_active else "white"
            graph.node(
                str(node.id),
                f"{node.name}\n({node.custom_type or 'Без типу'})",
                style="filled",
                fillcolor=color,
            )
            for child in node.get_children().filter(is_active=True):
                add_nodes(child)
                graph.edge(str(node.id), str(child.id))

        add_nodes(unit)
        svg_data = graph.pipe()
        return HttpResponse(svg_data, content_type="image/svg+xml")

    @extend_schema(
        summary="Отримати дітей певного підрозділу",
        parameters=[
            OpenApiParameter(
                name="parent_id",
                type=int,
                description="ID батьківського підрозділу",
                required=True,
            )
        ],
    )
    @action(detail=False, methods=["get"], url_path="children")
    def children(self, request):
        parent_id = request.query_params.get("parent_id")
        if not parent_id:
            return Response({"detail": "Не вказано parent_id"}, status=400)

        parent = self.get_queryset().filter(pk=parent_id).first()
        if parent is None:
            return Response({"detail": "Підрозділ не знайдено"}, status=404)

        children = self.get_queryset().filter(parent=parent)
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    def get_permission_unit(self, obj):
        return obj

    def perform_create(self, serializer):
        # Корінь — лише з глобальним company:write, дочірній — з правом на батька
        ensure_permission(
            self.request, "company:write", serializer.validated_data.get("parent")
        )
        serializer.save()

    def perform_update(self, serializer):
        if "parent" in serializer.validated_data:
            ensure_permission(
                self.request, "company:write", serializer.validated_data["parent"]
            )
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

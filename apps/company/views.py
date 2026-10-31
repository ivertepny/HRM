from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from graphviz import Digraph
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import StructuralUnit
from .serializers import HistorySerializer, StructuralUnitSerializer


class StructuralUnitViewSet(viewsets.ModelViewSet):
    serializer_class = StructuralUnitSerializer
    queryset = StructuralUnit.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if unit_type := self.request.query_params.get("type"):
            queryset = queryset.filter(custom_type=unit_type)
        return queryset.prefetch_related("children")

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

        try:
            parent = StructuralUnit.objects.get(pk=parent_id, is_active=True)
        except StructuralUnit.DoesNotExist:
            return Response({"detail": "Підрозділ не знайдено"}, status=404)

        children = parent.children.filter(is_active=True)
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.delete()

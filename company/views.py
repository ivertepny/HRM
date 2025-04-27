# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import StructuralUnit
from .serializers import StructuralUnitSerializer
from graphviz import Digraph
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class StructuralUnitViewSet(viewsets.ModelViewSet):
    serializer_class = StructuralUnitSerializer
    queryset = StructuralUnit.objects.filter(is_active=True)
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        if unit_type := self.request.query_params.get('type'):
            queryset = queryset.filter(custom_type=unit_type)
        return queryset.prefetch_related('children')

    @extend_schema(
        summary='Отримати історію змін',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                description='Кількість останніх записів',
                required=False
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        unit = self.get_object()
        history = unit.history.all().order_by('-history_date')
        if limit := request.query_params.get('limit'):
            history = history[:int(limit)]
        serializer = self.get_serializer(history, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Згенерувати діаграму',
        responses={
            200: OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def diagram(self, request, pk=None):
        unit = self.get_object()
        graph = Digraph(format='svg', graph_attr={'rankdir': 'TB'})

        def add_nodes(node):
            color = 'lightgrey' if not node.is_active else 'white'
            graph.node(
                str(node.id),
                f"{node.name}\n({node.custom_type or 'Без типу'})",
                style='filled',
                fillcolor=color
            )
            for child in node.get_children().filter(is_active=True):
                add_nodes(child)
                graph.edge(str(node.id), str(child.id))

        add_nodes(unit)
        svg_data = graph.pipe()
        return HttpResponse(svg_data, content_type='image/svg+xml')

    def perform_create(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise ValidationError(e.message_dict)

    def perform_destroy(self, instance):
        instance.delete()

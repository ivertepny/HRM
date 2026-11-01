from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from graphviz import Digraph, ExecutableNotFound
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.access.permissions import HasPermission, ensure_permission
from apps.access.services import scope_queryset
from apps.core.exceptions import ServiceUnavailable
from apps.employees.models import Employee

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
        working = Q(employees_su__date_fired__isnull=True) | Q(
            employees_su__date_fired__gt=timezone.localdate()
        )
        # distinct: два Count по різних зв'язках інакше перемножують рядки JOIN-а.
        # GROUP BY скидає Meta.ordering MPTT — порядок дерева задаємо явно.
        return queryset.annotate(
            active_children_count=Count(
                "children", filter=Q(children__is_active=True), distinct=True
            ),
            employees_count=Count("employees_su", filter=working, distinct=True),
        ).order_by("tree_id", "lft")

    @extend_schema(
        summary="Усе дерево підрозділів одним списком",
        description=(
            "Без пагінації, у порядку обходу дерева (tree_id, lft); у межах "
            "прав company:read. Для побудови дерева на клієнті."
        ),
        responses={200: StructuralUnitSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], pagination_class=None)
    def tree(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

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
    @action(detail=True, methods=["get"], pagination_class=None)
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
        # Стиль — як в інтерфейсі «Кадри»: чорнильний текст, тонкі рамки
        ink, line = "#1B2638", "#C3CBD5"
        graph = Digraph(
            format="svg",
            graph_attr={"rankdir": "TB", "bgcolor": "transparent", "nodesep": "0.3"},
            node_attr={
                "shape": "box",
                "style": "rounded,filled",
                "fillcolor": "white",
                "color": line,
                "fontcolor": ink,
                "fontname": "Helvetica, Arial, sans-serif",
                "fontsize": "11",
                "margin": "0.18,0.08",
            },
            edge_attr={"color": line, "arrowhead": "none"},
        )

        # Усе піддерево одним запитом, а не get_children() на кожен вузол
        subtree = unit.get_descendants(include_self=True).filter(is_active=True)
        for node in subtree:
            label = (
                f"{node.name}\n{node.custom_type}" if node.custom_type else node.name
            )
            is_root = node.pk == unit.pk
            graph.node(
                str(node.pk),
                label,
                **(
                    {"fillcolor": ink, "fontcolor": "white", "color": ink}
                    if is_root
                    else {}
                ),
            )
            if not is_root:
                graph.edge(str(node.parent_id), str(node.pk))

        try:
            svg_data = graph.pipe()
        except ExecutableNotFound as exc:
            raise ServiceUnavailable(
                "Діаграма недоступна: на сервері не встановлено Graphviz."
            ) from exc
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
    @action(detail=False, methods=["get"], url_path="children", pagination_class=None)
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
        # Закриття каскадне — не лишаємо працівників у закритих підрозділах
        subtree = instance.get_descendants(include_self=True)
        working = Employee.objects.filter(structural_unit__in=subtree).filter(
            Q(date_fired__isnull=True) | Q(date_fired__gt=timezone.localdate())
        )
        if count := working.count():
            raise ValidationError(
                {
                    "detail": f"У підрозділі та дочірніх є працівники ({count}) — "
                    "спершу переведіть їх в інші підрозділи."
                }
            )
        instance.delete()

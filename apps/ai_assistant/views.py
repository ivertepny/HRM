from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasPermission
from apps.access.services import get_access

from .models import AIQuery, ChatSession
from .serializers import (
    AIQuerySerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    ChatSessionSerializer,
)
from .services import answer

AI_PERMISSIONS = {"*": "ai:use"}


class ChatAPIView(APIView):
    permission_classes = [HasPermission]
    required_permissions = AI_PERMISSIONS

    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        tags=["AI Assistant"],
        summary="Надіслати питання AI-асистенту",
        description=(
            "Без session_id створює нову розмову; з ним — продовжує наявну "
            "(контекст — останні MAX_HISTORY_AI обмінів). Відповідає "
            "LangGraph-агент; оргструктуру бере інструментом з урахуванням "
            "прав. 503 — якщо LLM недоступна."
        ),
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if session_id := data.get("session_id"):
            session = get_object_or_404(
                ChatSession, user=request.user, session_id=session_id
            )
        else:
            session = ChatSession.objects.create(
                user=request.user, name=data.get("chat_session_name") or "Без назви"
            )

        query = answer(session, data["message"], get_access(request))
        return Response(
            {
                "session_id": session.session_id,
                "response": query.response,
                "query": AIQuerySerializer(query).data,
            }
        )


@extend_schema(
    tags=["AI Assistant"], summary="Уся історія запитів поточного користувача"
)
class ChatHistoryAPIView(generics.ListAPIView):
    queryset = AIQuery.objects.none()  # модель для схеми; дані — у get_queryset()
    serializer_class = AIQuerySerializer
    permission_classes = [HasPermission]
    required_permissions = AI_PERMISSIONS

    def get_queryset(self):
        return (
            AIQuery.objects.filter(user=self.request.user)
            .select_related("chat_session")
            .order_by("-created_at", "-id")
        )


@extend_schema_view(
    list=extend_schema(summary="Список чат-сесій користувача"),
    retrieve=extend_schema(summary="Чат-сесія"),
    partial_update=extend_schema(summary="Перейменувати чат-сесію"),
    destroy=extend_schema(summary="Видалити чат-сесію разом з повідомленнями"),
)
@extend_schema(tags=["AI Assistant"])
class ChatSessionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Сесії приватні: кожен бачить і змінює лише власні."""

    queryset = ChatSession.objects.none()  # модель для схеми; дані — у get_queryset()
    serializer_class = ChatSessionSerializer
    permission_classes = [HasPermission]
    required_permissions = AI_PERMISSIONS
    lookup_field = "session_id"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Для GROUP BY-запитів Django ігнорує Meta.ordering — задаємо явно
        return (
            ChatSession.objects.filter(user=self.request.user)
            .annotate(messages_count=Count("queries"))
            .order_by("-updated_at", "-id")
        )

    @extend_schema(
        summary="Повідомлення сесії", responses={200: AIQuerySerializer(many=True)}
    )
    @action(detail=True, methods=["get"])
    def messages(self, request, session_id=None):
        session = self.get_object()
        page = self.paginate_queryset(session.queries.select_related("chat_session"))
        return self.get_paginated_response(AIQuerySerializer(page, many=True).data)

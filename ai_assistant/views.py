# ai_assistant/views.py
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView

from drf_spectacular.utils import extend_schema

from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    AIQuerySerializer,
    ChatSessionSerializer,
)
from .openai_service import ask_openai
from .models import AIQuery, ChatSession


class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        tags=["AI Assistant"],
        summary="Надіслати питання AI-асистенту",
        description="Приймає повідомлення та повертає відповідь від OpenAI."
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data["message"]
            chat_session_name = serializer.validated_data.get("chat_session_name")
            user = request.user

            chat_session_id = request.session.get("chat_session_id")
            chat_session = None

            if chat_session_id:
                chat_session = ChatSession.objects.filter(session_id=chat_session_id, user=user).first()

            if not chat_session:
                # Генеруємо унікальний session_id
                session_id = str(uuid.uuid4())
                chat_session = ChatSession.objects.create(
                    user=user,
                    session_id=session_id,
                    name=chat_session_name or "Без назви"
                )
                request.session["chat_session_id"] = session_id
                request.session.modified = True
            elif chat_session_name and not chat_session.name:
                chat_session.name = chat_session_name
                chat_session.save()

            ai_response = ask_openai(user_message, user, request.session)

            return Response({"response": ai_response}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChatHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: AIQuerySerializer(many=True)},
        tags=["AI Assistant"],
        summary="Отримати історію спілкування з AI",
        description="Повертає історію повідомлень для поточного користувача."
    )
    def get(self, request):
        history = AIQuery.objects.filter(user=request.user).order_by('-created_at')
        serializer = AIQuerySerializer(history, many=True)
        return Response(serializer.data)


class ChatResetSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["AI Assistant"],
        summary="Скинути поточну сесію",
        description="Видаляє поточну чат-сесію і створює нову."
    )
    def post(self, request):
        user = request.user

        # Створення нової сесії
        new_chat_session = ChatSession.objects.create(user=user, name="Без назви")
        request.session["chat_session_id"] = new_chat_session.id
        request.session["chat_history"] = []
        request.session.modified = True

        return Response({
            "detail": "Сесію скинуто. Створено нову.",
            "new_chat_session_id": new_chat_session.id
        }, status=status.HTTP_200_OK)


class ChatSessionListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSessionSerializer

    @extend_schema(
        tags=["AI Assistant"],
        summary="Список чат-сесій користувача",
        description="Повертає всі сесії, пов’язані з поточним користувачем."
    )
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-created_at')


class ChatSessionHistoryAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AIQuerySerializer

    @extend_schema(
        tags=["AI Assistant"],
        summary="Отримати історію повідомлень по сесії",
        description="Повертає історію повідомлень певної чат-сесії."
    )
    def get(self, request, *args, **kwargs):
        session_id = kwargs.get("pk")
        session = ChatSession.objects.filter(user=request.user, id=session_id).first()
        if not session:
            return Response({"detail": "Сесію не знайдено."}, status=404)
        messages = AIQuery.objects.filter(chat_session=session).order_by('created_at')
        serializer = AIQuerySerializer(messages, many=True)
        return Response(serializer.data)


class ChatSessionRenameAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSessionSerializer
    queryset = ChatSession.objects.all()

    @extend_schema(
        tags=["AI Assistant"],
        summary="Перейменувати чат-сесію",
        description="Дозволяє змінити ім’я сесії користувача."
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"detail": "Доступ заборонено."}, status=403)
        return super().partial_update(request, *args, **kwargs)

# ai_assistant/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from drf_spectacular.utils import extend_schema

from .serializers import ChatRequestSerializer, ChatResponseSerializer, AIQuerySerializer
from .openai_service import ask_openai
from .models import AIQuery


class ChatAPIView(APIView):
    permission_classes = [AllowAny]  # Можно поменять на IsAuthenticated, если потребуется

    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        tags=["AI Assistant"],
        summary="Отправить вопрос AI-ассистенту",
        description="Принимает сообщение и возвращает ответ от OpenAI."
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data["message"]
            user = request.user if request.user.is_authenticated else None

            ai_response = ask_openai(user_message, user, request.session)

            if user and user.is_authenticated:
                AIQuery.objects.create(
                    user=user,
                    message=user_message,
                    response=ai_response
                )

            return Response({"response": ai_response}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: AIQuerySerializer(many=True)},
        tags=["AI Assistant"],
        summary="Получить историю общения с AI",
        description="Возвращает историю общения текущего пользователя."
    )
    def get(self, request):
        history = AIQuery.objects.filter(user=request.user).order_by('-created_at')
        serializer = AIQuerySerializer(history, many=True)
        return Response(serializer.data)


class ChatResetSessionAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["AI Assistant"],
        summary="Сбросить текущую сессию",
        description="Удаляет историю переписки в пределах текущей сессии."
    )
    def post(self, request):
        if 'last_ai_query_id' in request.session:
            del request.session['last_ai_query_id']
            request.session.modified = True
            return Response({"detail": "Сесія скинута."}, status=status.HTTP_200_OK)
        return Response({"detail": "Немає активної сесії."}, status=status.HTTP_200_OK)

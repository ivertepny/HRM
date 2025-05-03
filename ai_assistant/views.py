# ai_assistant/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import ChatRequestSerializer, ChatResponseSerializer, AIQuerySerializer
from .openai_service import ask_openai
from .models import AIQuery


class ChatAPIView(APIView):
    # permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]

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
            ai_response = ask_openai(user_message)

            AIQuery.objects.create(
                user=request.user,
                message=user_message,
                response=ai_response
            )

            return Response({"response": ai_response})
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

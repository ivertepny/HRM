# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from drf_spectacular.utils import extend_schema

from .serializers import ChatRequestSerializer, ChatResponseSerializer, AIQuerySerializer
from .openai_service import ask_openai
from .models import AIQuery


class ChatAPIView(APIView):
    permission_classes = [AllowAny]

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
            user = request.user if request.user.is_authenticated else None

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
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["AI Assistant"],
        summary="Скинути поточну сесію",
        description="Видаляє історію повідомлень у межах поточної сесії."
    )
    def post(self, request):
        keys_to_clear = ["last_user_message", "last_ai_response"]
        for key in keys_to_clear:
            if key in request.session:
                del request.session[key]
        request.session.modified = True
        return Response({"detail": "Сесія скинута."}, status=status.HTTP_200_OK)

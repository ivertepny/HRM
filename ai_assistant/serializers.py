# ai_assistant/serializers.py
from rest_framework import serializers
from .models import AIQuery, ChatSession


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    chat_session_name = serializers.CharField(required=False, allow_blank=True)


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()


class AIQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuery
        fields = ['id', 'message', 'response', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'user', 'name', 'created_at']
        read_only_fields = ['id', 'session_id', 'user', 'created_at']


# ai_assistant/serializers.py
from rest_framework import serializers
from .models import AIQuery


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()


class AIQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuery
        fields = ['id', 'message', 'response', 'created_at']

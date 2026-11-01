from rest_framework import serializers

from .models import AIQuery, ChatSession


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)
    session_id = serializers.UUIDField(
        required=False,
        help_text="Продовжити наявну розмову; без нього створюється нова сесія",
    )
    chat_session_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )


class AIQuerySerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="chat_session.session_id", read_only=True)
    tools_used = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        help_text="Інструменти агента, викликані для відповіді",
    )

    class Meta:
        model = AIQuery
        fields = ["id", "session_id", "message", "response", "tools_used", "created_at"]


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    response = serializers.CharField()
    query = AIQuerySerializer()


class ChatSessionSerializer(serializers.ModelSerializer):
    messages_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatSession
        fields = ["session_id", "name", "messages_count", "created_at", "updated_at"]
        read_only_fields = ["session_id", "created_at", "updated_at"]

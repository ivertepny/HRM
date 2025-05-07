# ai_assistant/models.py
from django.db import models
from django.conf import settings
from users.models import User


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Chat {self.id}"


class AIQuery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_queries')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='queries')

    def __str__(self):
        return f"Запит від {self.user} в {self.created_at.strftime('%Y-%m-%d %H:%M')}"

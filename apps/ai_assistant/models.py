import uuid

from django.db import models

from apps.users.models import User


class ChatSession(models.Model):
    """Розмова з асистентом. Клієнт ідентифікує її за session_id (UUID)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.name or f"Chat {self.session_id}"


class AIQuery(models.Model):
    """Один обмін у розмові: питання користувача і відповідь асистента."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_queries")
    chat_session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="queries"
    )
    message = models.TextField()
    response = models.TextField()
    # Інструменти агента, викликані під час відповіді (напр. get_company_structure)
    tools_used = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Запит від {self.user} в {self.created_at:%Y-%m-%d %H:%M}"

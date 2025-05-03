# ai_assistant/models.py
from django.db import models
from django.conf import settings


class AIQuery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_queries')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Запит від {self.user} в {self.created_at.strftime('%Y-%m-%d %H:%M')}"

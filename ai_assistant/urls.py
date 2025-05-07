# ai_assistant/urls.py
from django.urls import path
from .views import (
    ChatAPIView,
    ChatHistoryAPIView,
    ChatResetSessionAPIView,
    ChatSessionListAPIView,
    ChatSessionHistoryAPIView,
    ChatSessionRenameAPIView
)

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("chat/history/", ChatHistoryAPIView.as_view(), name="chat-history"),
    path("chat/reset/", ChatResetSessionAPIView.as_view(), name="chat-reset"),
    path("chat/sessions/", ChatSessionListAPIView.as_view(), name="chat-session-list"),
    path("chat/sessions/<int:pk>/history/", ChatSessionHistoryAPIView.as_view(), name="chat-session-history"),
    path("chat/sessions/<int:pk>/rename/", ChatSessionRenameAPIView.as_view(), name="chat-session-rename"),
]

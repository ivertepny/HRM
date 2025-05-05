# ai_assistant/urls.py
from django.urls import path
from .views import ChatAPIView, ChatHistoryAPIView, ChatResetSessionAPIView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='ai-chat'),
    path('history/', ChatHistoryAPIView.as_view(), name='ai-history'),
    path('reset-session/', ChatResetSessionAPIView.as_view(), name='ai-reset-session'),
]

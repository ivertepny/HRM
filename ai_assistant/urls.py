# ai_assistant/urls.py
from django.urls import path
from .views import ChatAPIView, ChatHistoryAPIView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='ai-chat'),
    path('history/', ChatHistoryAPIView.as_view(), name='ai-history'),
]

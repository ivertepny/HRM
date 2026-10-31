from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatAPIView, ChatHistoryAPIView, ChatSessionViewSet

router = DefaultRouter()
router.register(r"chat/sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("chat/history/", ChatHistoryAPIView.as_view(), name="chat-history"),
    *router.urls,
]

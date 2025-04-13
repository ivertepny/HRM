from django.urls import path
from .views import RegisterView, LoginView, UserListView, UserDetailView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserListView.as_view(), name='profile'),
    path('profile/<int:id>/', UserDetailView.as_view(), name='user-detail'),
]

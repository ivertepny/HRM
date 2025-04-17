from django.urls import path
from .views import RegisterView, LoginView, UserListView, UserDetailView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserListView.as_view(), name='profile'),
    path('profile/<int:id>/', UserDetailView.as_view(), name='user-detail'),
]

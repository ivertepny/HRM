from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.access.views import MyPermissionsView

from .views import (
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    UserDetailView,
    UserListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("me/permissions/", MyPermissionsView.as_view(), name="my-permissions"),
    path("profile/", UserListView.as_view(), name="profile"),
    path("profile/<int:id>/", UserDetailView.as_view(), name="user-detail"),
]

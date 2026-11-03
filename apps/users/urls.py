from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.access.views import MyPermissionsView

from .views import (
    InviteAcceptView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendInviteView,
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
    path("profile/<int:id>/invite/", ResendInviteView.as_view(), name="user-invite"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("invite/accept/", InviteAcceptView.as_view(), name="invite-accept"),
]

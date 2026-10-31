from django.db.models import Q
from django.utils.timezone import now
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.access.permissions import HasPermission
from apps.access.services import get_access, grant_default_role, scope_queryset

from .models import User
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserAdminSerializer,
    UserSerializer,
)

USER_PERMISSIONS = {
    "read": "users:read",
    "write": "users:write",
    "DELETE": "users:delete",
}


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(generics.CreateAPIView):
    """Створення облікового запису (HR / адмін). Публічної реєстрації немає."""

    queryset = User.objects.all()
    permission_classes = [HasPermission]
    required_permissions = USER_PERMISSIONS
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        grant_default_role(user, granted_by=self.request.user)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token = get_tokens_for_user(user)
        # Update last login time
        user.last_login = now()
        user.save(update_fields=["last_login"])
        return Response({"token": token, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except KeyError:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TokenError:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserScopeMixin:
    """Користувачі видимі глобально (users:read) або в межах підрозділів
    scoped-ролі (через профіль працівника); себе видно завжди."""

    permission_classes = [HasPermission]
    required_permissions = USER_PERMISSIONS

    def get_queryset(self):
        return scope_queryset(
            self.request,
            User.objects.order_by("id"),
            "users:read",
            unit_field="employee_profile__structural_unit",
            owner=Q(pk=self.request.user.pk),
        )

    def is_owner(self, obj):
        return obj.pk == self.request.user.pk

    def get_permission_unit(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.structural_unit if profile else None

    def get_serializer_class(self):
        if get_access(self.request).has_anywhere("users:write"):
            return UserAdminSerializer
        return UserSerializer


class UserListView(UserScopeMixin, generics.ListAPIView):
    pass


class UserDetailView(UserScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    lookup_field = "id"
    # Свій профіль можна читати і редагувати (лише ім'я), але не видаляти
    owner_methods = ("GET", "HEAD", "OPTIONS", "PUT", "PATCH")

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError(
                {"detail": "Не можна видалити власний обліковий запис."}
            )
        instance.delete()


class MeView(generics.RetrieveUpdateAPIView):
    """Профіль поточного користувача."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

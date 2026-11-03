from django.db.models import Q
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.access.permissions import HasPermission
from apps.access.services import get_access, grant_default_role, scope_queryset
from apps.core.exceptions import ServiceUnavailable
from apps.core.throttling import LoginEmailThrottle, PasswordResetEmailThrottle
from apps.slack import notify as slack

from .emails import invite_link, send_invite, send_password_reset, try_send
from .filters import UserFilter
from .models import User
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    UserAdminSerializer,
    UserSerializer,
)
from .tokens import invite_token, password_reset_token

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


@extend_schema(
    summary="Створити обліковий запис і надіслати запрошення",
    description=(
        "Пароль задає сама людина за посиланням з листа. invite_sent=false — "
        "лист не пішов; запис створено, запрошення можна надіслати ще раз."
    ),
)
class RegisterView(generics.CreateAPIView):
    """Створення облікового запису (HR / адмін). Публічної реєстрації немає."""

    queryset = User.objects.all()
    permission_classes = [HasPermission]
    required_permissions = USER_PERMISSIONS
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        grant_default_role(user, granted_by=self.request.user)
        # Невдале надсилання не скасовує створений запис — HR надішле ще раз
        user.invite_sent = try_send(send_invite, user, invited_by=self.request.user)
        slack.invite(user, invite_link(user))


def revoke_sessions(user):
    """Усі refresh-токени користувача — у blacklist (вихід на всіх пристроях)."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginEmailThrottle]

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
            User.objects.select_related("employee_profile").order_by("id"),
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
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]


# Серіалізатор залежить від прав; у схемі показуємо адмінську версію запису
# (власник змінює лише ім'я — зайві поля для нього read-only на бекенді)
@extend_schema_view(
    get=extend_schema(responses=UserAdminSerializer),
    put=extend_schema(request=UserAdminSerializer, responses=UserAdminSerializer),
    patch=extend_schema(request=UserAdminSerializer, responses=UserAdminSerializer),
)
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


@extend_schema(
    summary="Надіслати запрошення ще раз",
    description="Лише поки людина не задала пароль; інакше — скидання пароля.",
    request=None,
    responses={204: None},
)
class ResendInviteView(UserScopeMixin, generics.GenericAPIView):
    lookup_field = "id"
    required_permissions = {"POST": "users:write"}

    def post(self, request, id):
        user = self.get_object()
        if user.has_usable_password():
            raise ValidationError(
                {"detail": "Пароль уже задано — людина може скинути його сама."}
            )
        if not user.is_active:
            raise ValidationError({"detail": "Обліковий запис вимкнено."})
        if not try_send(send_invite, user, invited_by=request.user):
            raise ServiceUnavailable("Не вдалося надіслати лист. Спробуйте пізніше.")
        slack.invite(user, invite_link(user))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Запит на скидання пароля",
    description=(
        "Завжди 204, незалежно від того, чи є такий обліковий запис (щоб не "
        "можна було перевіряти пошти). Лист отримують лише активні записи."
    ),
    responses={204: None},
)
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetEmailThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            try_send(send_password_reset, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetPasswordView(generics.GenericAPIView):
    """Новий пароль за посиланням з листа; generator — вид токена."""

    serializer_class = SetPasswordSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    generator = None

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "generator": self.generator}

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["password"])
        # Перехід за посиланням з листа підтверджує, що пошта — його
        user.is_email_confirmed = True
        user.save(update_fields=["password", "is_email_confirmed"])
        revoke_sessions(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Задати новий пароль за посиланням зі скидання",
    responses={204: None},
)
class PasswordResetConfirmView(SetPasswordView):
    generator = password_reset_token


@extend_schema(
    summary="Прийняти запрошення: задати пароль",
    responses={204: None},
)
class InviteAcceptView(SetPasswordView):
    generator = invite_token


class MeView(generics.RetrieveUpdateAPIView):
    """Профіль поточного користувача."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

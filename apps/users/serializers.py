from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User
from .tokens import user_for_token


class UserSerializer(serializers.ModelSerializer):
    """Профіль для самого користувача: змінювати можна лише ім'я."""

    employee = serializers.SerializerMethodField(
        help_text="id профілю працівника або null, якщо його ще не оформлено"
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "status",
            "employee",
            "is_email_confirmed",
            "created_at",
            "updated_at",
            "last_login",
        ]
        read_only_fields = [
            "email",
            "status",
            "is_email_confirmed",
            "created_at",
            "updated_at",
            "last_login",
        ]

    def get_employee(self, obj) -> int | None:
        profile = getattr(obj, "employee_profile", None)
        return profile.id if profile else None


class UserAdminSerializer(UserSerializer):
    """Для users:write — також email і статус."""

    invite_pending = serializers.SerializerMethodField(
        help_text="Пароль ще не задано — запрошення не прийнято"
    )

    class Meta(UserSerializer.Meta):
        fields = [*UserSerializer.Meta.fields, "invite_pending"]
        read_only_fields = [
            "is_email_confirmed",
            "created_at",
            "updated_at",
            "last_login",
        ]

    def get_invite_pending(self, obj) -> bool:
        return not obj.has_usable_password()

    def validate_status(self, value):
        request = self.context.get("request")
        if (
            request is not None
            and self.instance is not None
            and self.instance.pk == request.user.pk
            and value != self.instance.status
        ):
            raise serializers.ValidationError(
                "Не можна змінити статус власного акаунта."
            )
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """Новий обліковий запис без пароля: людина задає його сама за запрошенням."""

    invite_sent = serializers.SerializerMethodField(
        help_text="false — лист не пішов (див. логи), надішліть запрошення ще раз"
    )

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "invite_sent"]

    def get_invite_sent(self, obj) -> bool:
        return getattr(obj, "invite_sent", False)

    def create(self, validated_data):
        # password=None — непридатний пароль: увійти неможливо до запрошення
        return User.objects.create_user(password=None, **validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SetPasswordSerializer(serializers.Serializer):
    """Новий пароль за посиланням з листа (запрошення або скидання)."""

    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    INVALID_LINK = "Посилання недійсне або застаріло. Попросіть нове."

    def validate(self, attrs):
        user = user_for_token(attrs["uid"], attrs["token"], self.context["generator"])
        if user is None:
            raise serializers.ValidationError({"token": self.INVALID_LINK})
        # Валідатори з AUTH_PASSWORD_VALIDATORS (довжина, схожість з email тощо)
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        attrs["user"] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User is inactive")
        return user


class LogoutSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)

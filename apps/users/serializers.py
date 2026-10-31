from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Профіль для самого користувача: змінювати можна лише ім'я."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "status",
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


class UserAdminSerializer(UserSerializer):
    """Для users:write — також email і статус."""

    class Meta(UserSerializer.Meta):
        read_only_fields = [
            "is_email_confirmed",
            "created_at",
            "updated_at",
            "last_login",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password"]

    def validate(self, attrs):
        # Валідатори з AUTH_PASSWORD_VALIDATORS (довжина, схожість з email тощо)
        candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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

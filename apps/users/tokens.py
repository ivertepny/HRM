"""Одноразові токени для посилань у листах: скидання пароля і запрошення.

Основа — PasswordResetTokenGenerator Django: у хеші пароль, останній вхід і
email, тож токен перестає діяти, щойно пароль встановлено, користувач увійшов
або йому змінили пошту. Різний key_salt — токен запрошення не підійде для
скидання і навпаки.
"""

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    base36_to_int,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)

from .models import User


class TimedTokenGenerator(PasswordResetTokenGenerator):
    """Django перевіряє лише глобальний PASSWORD_RESET_TIMEOUT (у нас — найдовший
    з термінів); власний, коротший ліміт кожного виду токена — поверх нього."""

    def __init__(self, key_salt, setting):
        super().__init__()
        self.key_salt = key_salt
        self.setting = setting

    @property
    def max_age(self):
        return getattr(settings, self.setting)

    def check_token(self, user, token):
        if not super().check_token(user, token):
            return False
        issued = base36_to_int(token.split("-")[0])
        return self._num_seconds(self._now()) - issued <= self.max_age


password_reset_token = TimedTokenGenerator(
    "apps.users.password_reset", "PASSWORD_RESET_TOKEN_SECONDS"
)
invite_token = TimedTokenGenerator("apps.users.invite", "INVITE_TOKEN_SECONDS")


def encode_uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def user_for_token(uid, token, generator):
    """Користувач за uid з посилання — лише активний і з чинним токеном."""
    try:
        pk = int(force_str(urlsafe_base64_decode(uid)))
    except TypeError, ValueError, OverflowError:
        return None
    user = User.objects.filter(pk=pk, is_active=True).first()
    if user is None or not generator.check_token(user, token):
        return None
    return user

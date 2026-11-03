"""Ліміти запитів (ставки — у settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]).

До Django ходить лише Next (BFF), тож IP у запиті — завжди адреса контейнера
Next. Ліміт за адресою клієнта робить nginx стеку; тут — за тим, що Django
знає напевно: користувачем або email у формі входу.
"""

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class AuthenticatedUserThrottle(UserRateThrottle):
    """Загальний ліміт на користувача. Анонімні запити (вхід, refresh, health)
    не рахуються: без справжнього IP вони ділили б один лічильник на всіх."""

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return super().get_cache_key(request, view)


class LoginEmailThrottle(SimpleRateThrottle):
    """Підбір пароля до конкретного облікового запису — навіть з різних IP."""

    scope = "login"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": email.strip().lower(),
        }


class AIChatThrottle(UserRateThrottle):
    """Кожне повідомлення асистенту — платний виклик моделі."""

    scope = "ai_chat"


class AIChatDailyThrottle(UserRateThrottle):
    scope = "ai_chat_daily"

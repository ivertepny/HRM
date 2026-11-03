import re
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.users.tests.factories import UserFactory
from apps.users.tokens import encode_uid, invite_token, password_reset_token

pytestmark = pytest.mark.django_db

REGISTER = "/api/users/register/"
RESET = "/api/users/password-reset/"
RESET_CONFIRM = "/api/users/password-reset/confirm/"
INVITE_ACCEPT = "/api/users/invite/accept/"
NEW_PASSWORD = "Fresh-start-2026!"


def link_params(message):
    """uid і token з посилання в листі."""
    url = re.search(r"https?://\S+", message.body).group(0)
    query = parse_qs(urlparse(url).query)
    return url, {"uid": query["uid"][0], "token": query["token"][0]}


# --- запрошення ----------------------------------------------------------------


def test_hr_creates_account_and_invite_is_sent(client_as, user, grant, mailoutbox):
    grant(user, "users:write")

    response = client_as(user).post(
        REGISTER,
        {"email": "new@example.com", "first_name": "Іван", "last_name": "Петренко"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["invite_sent"] is True
    created = User.objects.get(email="new@example.com")
    assert not created.has_usable_password()  # увійти до запрошення неможливо

    [message] = mailoutbox
    assert message.to == ["new@example.com"]
    url, _ = link_params(message)
    assert url.startswith("http://localhost:3000/invite?uid=")
    assert "Іван" in message.body


def test_register_ignores_password_from_client(auth_client, mailoutbox):
    auth_client.post(
        REGISTER,
        {"email": "new@example.com", "password": "Chosen-by-HR-1"},
        format="json",
    )
    assert not User.objects.get(email="new@example.com").has_usable_password()


def test_account_is_created_even_if_mail_fails(auth_client):
    with patch("apps.users.emails.send_mail", side_effect=OSError("smtp down")):
        response = auth_client.post(
            REGISTER, {"email": "new@example.com"}, format="json"
        )

    assert response.status_code == 201
    assert response.json()["invite_sent"] is False
    assert User.objects.filter(email="new@example.com").exists()


def test_accept_invite_sets_password_and_confirms_email(
    auth_client, api_client, mailoutbox, password
):
    auth_client.post(REGISTER, {"email": "new@example.com"}, format="json")
    _, params = link_params(mailoutbox[0])

    response = api_client.post(
        INVITE_ACCEPT, {**params, "password": NEW_PASSWORD}, format="json"
    )

    assert response.status_code == 204
    user = User.objects.get(email="new@example.com")
    assert user.check_password(NEW_PASSWORD)
    assert user.is_email_confirmed
    login = api_client.post(
        "/api/users/login/",
        {"email": user.email, "password": NEW_PASSWORD},
        format="json",
    )
    assert login.status_code == 200


def test_invite_link_works_only_once(auth_client, api_client, mailoutbox):
    auth_client.post(REGISTER, {"email": "new@example.com"}, format="json")
    _, params = link_params(mailoutbox[0])
    api_client.post(INVITE_ACCEPT, {**params, "password": NEW_PASSWORD}, format="json")

    again = api_client.post(
        INVITE_ACCEPT, {**params, "password": "Another-pass-2026"}, format="json"
    )

    assert again.status_code == 400
    assert "token" in again.json()


def test_weak_password_rejected_on_accept(auth_client, api_client, mailoutbox):
    auth_client.post(REGISTER, {"email": "new@example.com"}, format="json")
    _, params = link_params(mailoutbox[0])

    response = api_client.post(
        INVITE_ACCEPT, {**params, "password": "12345"}, format="json"
    )

    assert response.status_code == 400
    assert "password" in response.json()


def test_invite_token_does_not_reset_password(api_client):
    user = UserFactory()
    params = {"uid": encode_uid(user), "token": invite_token.make_token(user)}

    response = api_client.post(
        RESET_CONFIRM, {**params, "password": NEW_PASSWORD}, format="json"
    )
    assert response.status_code == 400


def test_resend_invite(client_as, user, grant, mailoutbox):
    grant(user, "users:read", "users:write")
    invited = User.objects.create_user(email="later@example.com", password=None)
    client = client_as(user)

    assert client.post(f"/api/users/profile/{invited.id}/invite/").status_code == 204
    assert len(mailoutbox) == 1
    # Для людини з паролем — ні: їй є скидання пароля
    other = UserFactory()
    assert client.post(f"/api/users/profile/{other.id}/invite/").status_code == 400


def test_resend_invite_requires_users_write(client_as, user):
    invited = User.objects.create_user(email="later@example.com", password=None)
    response = client_as(user).post(f"/api/users/profile/{invited.id}/invite/")
    assert response.status_code in (403, 404)


def test_admin_sees_pending_invite(auth_client):
    invited = User.objects.create_user(email="later@example.com", password=None)
    body = auth_client.get(f"/api/users/profile/{invited.id}/").json()
    assert body["invite_pending"] is True


# --- скидання пароля -------------------------------------------------------------


def test_reset_request_sends_link(api_client, mailoutbox):
    user = UserFactory(email="olena@example.com")

    response = api_client.post(RESET, {"email": "OLENA@example.com"}, format="json")

    assert response.status_code == 204
    [message] = mailoutbox
    assert message.to == [user.email]
    url, _ = link_params(message)
    assert url.startswith("http://localhost:3000/reset-password?uid=")


@pytest.mark.parametrize("active", [False, None])
def test_reset_request_reveals_nothing(api_client, mailoutbox, active):
    if active is False:
        UserFactory(email="gone@example.com", status="inactive")

    response = api_client.post(RESET, {"email": "gone@example.com"}, format="json")

    assert response.status_code == 204
    assert mailoutbox == []


def test_reset_confirm_changes_password_and_ends_sessions(
    api_client, mailoutbox, password
):
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    api_client.post(RESET, {"email": user.email}, format="json")
    _, params = link_params(mailoutbox[0])

    response = api_client.post(
        RESET_CONFIRM, {**params, "password": NEW_PASSWORD}, format="json"
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
    old = api_client.post(
        "/api/users/token/refresh/", {"refresh": str(refresh)}, format="json"
    )
    assert old.status_code == 401


def test_reset_link_expires(api_client):
    user = UserFactory()
    params = {"uid": encode_uid(user), "token": password_reset_token.make_token(user)}

    # Django рахує час токенів у наївному локальному datetime.now()
    later = datetime.now() + timedelta(hours=2, minutes=1)
    with patch.object(password_reset_token, "_now", return_value=later):
        response = api_client.post(
            RESET_CONFIRM, {**params, "password": NEW_PASSWORD}, format="json"
        )

    assert response.status_code == 400


def test_garbage_link_rejected(api_client):
    response = api_client.post(
        RESET_CONFIRM,
        {"uid": "!!!", "token": "nope", "password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    assert "token" in response.json()


def test_reset_request_is_rate_limited_per_email(api_client, throttle_rates):
    from rest_framework.throttling import SimpleRateThrottle

    SimpleRateThrottle.THROTTLE_RATES = {
        **SimpleRateThrottle.THROTTLE_RATES,
        "password_reset": "1/hour",
    }
    UserFactory(email="olena@example.com")

    assert api_client.post(RESET, {"email": "olena@example.com"}).status_code == 204
    assert api_client.post(RESET, {"email": "olena@example.com"}).status_code == 429

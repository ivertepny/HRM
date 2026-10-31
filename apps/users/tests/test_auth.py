import pytest

from apps.users.models import User

pytestmark = pytest.mark.django_db


def login(api_client, email, password):
    return api_client.post(
        "/api/users/login/", {"email": email, "password": password}, format="json"
    )


def test_register_creates_user_with_hashed_password(api_client, password):
    response = api_client.post(
        "/api/users/register/",
        {
            "email": "new@example.com",
            "password": password,
            "first_name": "Ivan",
            "last_name": "Petrenko",
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="new@example.com")
    assert user.check_password(password)
    assert "password" not in response.json()


def test_register_rejects_duplicate_email(api_client, user, password):
    response = api_client.post(
        "/api/users/register/",
        {"email": user.email, "password": password},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()


def test_login_returns_token_pair_and_user(api_client, user, password):
    response = login(api_client, user.email, password)

    assert response.status_code == 200
    body = response.json()
    assert set(body["token"]) == {"access", "refresh"}
    assert body["user"]["email"] == user.email


def test_login_with_wrong_password_returns_400(api_client, user):
    response = login(api_client, user.email, "wrong-password")

    assert response.status_code == 400


def test_refresh_returns_new_access_and_rotates_refresh(api_client, user, password):
    refresh = login(api_client, user.email, password).json()["token"]["refresh"]

    response = api_client.post(
        "/api/users/token/refresh/", {"refresh": refresh}, format="json"
    )

    assert response.status_code == 200
    assert set(response.json()) == {"access", "refresh"}

    # Ротація + blacklist: старий refresh більше не приймається
    reused = api_client.post(
        "/api/users/token/refresh/", {"refresh": refresh}, format="json"
    )
    assert reused.status_code == 401


def test_logout_blacklists_refresh_token(api_client, user, password):
    tokens = login(api_client, user.email, password).json()["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        "/api/users/logout/", {"refresh": tokens["refresh"]}, format="json"
    )

    assert response.status_code == 205
    reused = api_client.post(
        "/api/users/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
    )
    assert reused.status_code == 401


def test_jwt_access_token_authenticates_requests(api_client, user, password):
    access = login(api_client, user.email, password).json()["token"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get("/api/users/profile/")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        "/api/users/profile/",
        "/api/employees/employees/",
        "/api/company/units/",
        "/api/ai/chat/sessions/",
    ],
)
def test_protected_endpoints_require_authentication(api_client, url):
    assert api_client.get(url).status_code == 401

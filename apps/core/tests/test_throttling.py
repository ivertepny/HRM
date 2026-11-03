import pytest

from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/users/login/"


def test_login_limited_per_email_case_insensitive(api_client, throttle_rates, password):
    user = UserFactory(email="olena@example.com")
    attempt = {"email": user.email, "password": "wrong"}

    assert api_client.post(LOGIN, attempt, format="json").status_code == 400
    assert (
        api_client.post(
            LOGIN, {**attempt, "email": " OLENA@example.com "}, format="json"
        ).status_code
        == 400
    )
    # Третя спроба — навіть з правильним паролем
    response = api_client.post(
        LOGIN, {"email": user.email, "password": password}, format="json"
    )
    assert response.status_code == 429
    assert response.json()["detail"].startswith("Забагато запитів. Спробуйте за ")
    assert "Retry-After" in response


def test_login_limit_is_per_account(api_client, throttle_rates, password):
    first, second = UserFactory(), UserFactory()
    for _ in range(2):
        api_client.post(LOGIN, {"email": first.email, "password": "x"}, format="json")

    response = api_client.post(
        LOGIN, {"email": second.email, "password": password}, format="json"
    )
    assert response.status_code == 200


def test_authenticated_requests_limited_per_user(client_as, throttle_rates):
    user, other = UserFactory(), UserFactory()
    client = client_as(user)
    codes = [client.get("/api/users/me/").status_code for _ in range(4)]

    assert codes == [200, 200, 200, 429]
    assert client_as(other).get("/api/users/me/").status_code == 200


def test_anonymous_requests_not_limited_by_user_throttle(api_client, throttle_rates):
    codes = {api_client.get("/api/health/").status_code for _ in range(5)}
    assert codes == {200}

"""Sign-up, sign-in, tokens."""

from httpx import AsyncClient

from tests.api.helpers import API, PASSWORD, bearer, error_code, register


async def test_parent_can_register_and_is_signed_in(client: AsyncClient):
    parent = await register(client, role="parent", full_name="  Sunita Sharma ")

    assert parent.user["role"] == "parent"
    assert parent.user["full_name"] == "Sunita Sharma"
    assert "password" not in str(parent.user).lower()
    assert parent.tokens["token_type"] == "bearer"
    assert parent.tokens["expires_in"] == 30 * 60

    me = await client.get(f"{API}/auth/me", headers=parent.headers)
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == parent.email
    assert body["active_role"] == "parent"
    assert body["active_student"] is None
    assert body["onboarding_complete"] is False  # no child added yet


async def test_student_can_register_and_gets_a_learner_record(client: AsyncClient):
    student = await register(client, role="student", full_name="Kabir Verma")

    me = (await client.get(f"{API}/auth/me", headers=student.headers)).json()
    assert me["active_role"] == "student"
    assert me["active_student"]["name"] == "Kabir Verma"
    assert me["active_student"]["has_own_login"] is True
    assert me["active_student"]["profile"] is None
    assert me["onboarding_complete"] is False  # class details not filled in yet


async def test_email_is_not_case_sensitive(client: AsyncClient):
    await register(client, email="Mixed.Case@Example.com")

    duplicate = await client.post(
        f"{API}/auth/register",
        json={
            "role": "parent",
            "full_name": "Again",
            "email": "mixed.case@example.com",
            "password": PASSWORD,
        },
    )
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "email_already_registered"

    login = await client.post(
        f"{API}/auth/login", json={"email": "MIXED.CASE@EXAMPLE.COM", "password": PASSWORD}
    )
    assert login.status_code == 200


async def test_login_returns_working_tokens(client: AsyncClient):
    parent = await register(client)

    login = await client.post(f"{API}/auth/login", json={"email": parent.email, "password": parent.password})
    assert login.status_code == 200
    token = login.json()["tokens"]["access_token"]

    me = await client.get(f"{API}/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == parent.user["id"]


async def test_wrong_password_and_unknown_email_look_the_same(client: AsyncClient):
    parent = await register(client)

    wrong_password = await client.post(
        f"{API}/auth/login", json={"email": parent.email, "password": "nope-nope-nope"}
    )
    unknown_email = await client.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": parent.password}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert error_code(wrong_password) == "invalid_credentials"


async def test_refresh_gives_new_working_tokens(client: AsyncClient):
    parent = await register(client)

    refreshed = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": parent.tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200

    me = await client.get(f"{API}/auth/me", headers=bearer(refreshed.json()["access_token"]))
    assert me.status_code == 200


async def test_refresh_token_cannot_be_used_to_call_the_api(client: AsyncClient):
    parent = await register(client)
    response = await client.get(f"{API}/auth/me", headers=bearer(parent.tokens["refresh_token"]))
    assert response.status_code == 401
    assert error_code(response) == "invalid_token"


async def test_access_token_cannot_be_used_to_refresh(client: AsyncClient):
    parent = await register(client)
    response = await client.post(f"{API}/auth/refresh", json={"refresh_token": parent.tokens["access_token"]})
    assert response.status_code == 401


async def test_requests_without_a_valid_token_are_rejected(client: AsyncClient):
    missing = await client.get(f"{API}/auth/me")
    assert missing.status_code == 401
    assert error_code(missing) == "not_authenticated"
    assert missing.headers["WWW-Authenticate"] == "Bearer"

    garbage = await client.get(f"{API}/auth/me", headers=bearer("not-a-real-token"))
    assert garbage.status_code == 401
    assert error_code(garbage) == "invalid_token"


async def test_registration_input_is_validated(client: AsyncClient):
    response = await client.post(
        f"{API}/auth/register",
        json={"role": "teacher", "full_name": " ", "email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert {detail["field"] for detail in body["details"]} == {"role", "full_name", "email", "password"}
    assert "short" not in response.text, "submitted values (like passwords) must never be echoed back"


async def test_unsupported_interface_language_is_rejected(client: AsyncClient):
    response = await client.post(
        f"{API}/auth/register",
        json={
            "role": "parent",
            "full_name": "Meena",
            "email": "meena@example.com",
            "password": PASSWORD,
            "preferred_language": "ta",  # registered for the future, not switched on yet
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "preferred_language"


async def test_hindi_and_hinglish_are_accepted_as_interface_language(client: AsyncClient):
    for language in ("hi", "hinglish"):
        account = await register(client, preferred_language=language)
        assert account.user["preferred_language"] == language

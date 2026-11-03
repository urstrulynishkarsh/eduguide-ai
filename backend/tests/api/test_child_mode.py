"""Child mode: a parent hands the device to one child."""

from httpx import AsyncClient

from tests.api.helpers import API, add_child, child_payload, error_code, register, start_child_session


async def test_parent_starts_child_mode(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)

    response = await client.post(f"{API}/students/{child['id']}/session", headers=parent.headers)

    assert response.status_code == 200
    body = response.json()
    assert body["student"]["id"] == child["id"]
    assert body["expires_in"] == 720 * 60
    assert "refresh_token" not in body

    me = (
        await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    ).json()
    assert me["active_role"] == "student"
    assert me["active_student"]["id"] == child["id"]
    assert me["user"]["role"] == "parent"  # still the parent's account underneath
    assert me["onboarding_complete"] is True


async def test_child_mode_sees_only_that_child(client: AsyncClient):
    parent = await register(client)
    aarav = await add_child(client, parent)
    anaya = await add_child(client, parent, class_level="ukg")
    aarav_session = await start_child_session(client, parent, aarav["id"])

    listed = (await client.get(f"{API}/students", headers=aarav_session)).json()
    assert [student["id"] for student in listed] == [aarav["id"]]

    own = await client.get(f"{API}/students/{aarav['id']}", headers=aarav_session)
    assert own.status_code == 200

    sibling = await client.get(f"{API}/students/{anaya['id']}", headers=aarav_session)
    assert sibling.status_code == 404


async def test_child_mode_cannot_change_anything_or_reach_parent_features(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    session = await start_child_session(client, parent, child["id"])
    url = f"{API}/students/{child['id']}"

    forbidden = [
        await client.patch(url, json={"name": "Boss"}, headers=session),
        await client.put(f"{url}/profile", json={"class_level": "class_1", "board": "cbse"}, headers=session),
        await client.delete(url, headers=session),
        await client.post(f"{API}/students", json=child_payload(), headers=session),
        await client.post(f"{url}/session", headers=session),
    ]
    for response in forbidden:
        assert response.status_code == 403, response.request.method
        assert error_code(response) == "parent_required"

    unchanged = (await client.get(url, headers=parent.headers)).json()
    assert unchanged["name"] == "Aarav"
    assert unchanged["profile"]["class_level"] == "class_7"


async def test_child_session_stops_working_when_the_child_is_removed(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    session = await start_child_session(client, parent, child["id"])

    await client.delete(f"{API}/students/{child['id']}", headers=parent.headers)

    response = await client.get(f"{API}/auth/me", headers=session)
    assert response.status_code == 401
    assert error_code(response) == "invalid_token"

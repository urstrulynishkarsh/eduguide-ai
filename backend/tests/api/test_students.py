"""Adding and managing children, and keeping families apart."""

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient

from tests.api.helpers import API, add_child, child_payload, error_code, register


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value)


async def test_parent_adds_a_child(client: AsyncClient):
    parent = await register(client)

    response = await client.post(f"{API}/students", json=child_payload(), headers=parent.headers)

    assert response.status_code == 201
    child = response.json()
    assert child["name"] == "Aarav"
    assert child["age"] == 12
    assert child["has_own_login"] is False
    assert child["profile"] == {
        "class_level": "class_7",
        "class_label": "Class 7",
        "band": "middle",
        "board": "cbse",
        "board_name": None,
        "medium": "en",
        "primary_language": "hinglish",
        "stream": None,
        "goal": "school_exam",  # the default for Class 7
        "subjects": ["Mathematics", "Science"],
    }

    me = (await client.get(f"{API}/auth/me", headers=parent.headers)).json()
    assert me["onboarding_complete"] is True


async def test_parent_lists_children_in_the_order_they_were_added(client: AsyncClient):
    parent = await register(client)
    first = await add_child(client, parent)
    second = (
        await client.post(
            f"{API}/students",
            json={"name": "Anaya", "age": 5, "profile": {"class_level": "ukg", "board": "cbse"}},
            headers=parent.headers,
        )
    ).json()

    response = await client.get(f"{API}/students", headers=parent.headers)

    assert response.status_code == 200
    assert [child["id"] for child in response.json()] == [first["id"], second["id"]]
    assert second["profile"]["band"] == "foundational"
    assert second["profile"]["goal"] == "general_learning"


async def test_parent_updates_name_and_age(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)

    response = await client.patch(
        f"{API}/students/{child['id']}", json={"name": "Aarav Sharma"}, headers=parent.headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Aarav Sharma"
    assert response.json()["age"] == 12  # untouched
    assert _time(response.json()["updated_at"]) > _time(child["updated_at"])
    assert response.json()["created_at"] == child["created_at"]

    cleared = await client.patch(f"{API}/students/{child['id']}", json={"age": None}, headers=parent.headers)
    assert cleared.json()["age"] is None

    no_name = await client.patch(f"{API}/students/{child['id']}", json={"name": None}, headers=parent.headers)
    assert no_name.status_code == 422


async def test_parent_moves_child_to_the_next_class(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)

    response = await client.put(
        f"{API}/students/{child['id']}/profile",
        json={"class_level": "class_8", "board": "state", "board_name": "MP Board", "medium": "hi"},
        headers=parent.headers,
    )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["class_level"] == "class_8"
    assert profile["board_name"] == "MP Board"
    assert profile["medium"] == "hi"
    assert profile["subjects"] == []  # PUT replaces the whole profile

    fetched = await client.get(f"{API}/students/{child['id']}", headers=parent.headers)
    assert fetched.json()["profile"] == profile


async def test_board_name_is_only_kept_for_state_and_other_boards(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent, board="cbse", board_name="Should be dropped")
    assert child["profile"]["board_name"] is None


async def test_subjects_are_cleaned(client: AsyncClient):
    parent = await register(client)
    child = await add_child(
        client, parent, subjects=["  Mathematics ", "mathematics", "", "Social   Science"]
    )
    assert child["profile"]["subjects"] == ["Mathematics", "Social Science"]


async def test_parent_removes_a_child(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)

    deleted = await client.delete(f"{API}/students/{child['id']}", headers=parent.headers)
    assert deleted.status_code == 204

    gone = await client.get(f"{API}/students/{child['id']}", headers=parent.headers)
    assert gone.status_code == 404
    assert (await client.get(f"{API}/students", headers=parent.headers)).json() == []


async def test_class_12_science_student_preparing_for_jee(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent, class_level="class_12", stream="science", goal="jee")
    assert child["profile"]["band"] == "senior_secondary"
    assert child["profile"]["stream"] == "science"
    assert child["profile"]["goal"] == "jee"


@pytest.mark.parametrize(
    ("profile", "field"),
    [
        ({"class_level": "class_11"}, "stream"),  # Class 11 needs a stream
        ({"class_level": "class_7", "stream": "science"}, "stream"),  # too early for a stream
        ({"class_level": "class_7", "goal": "jee"}, "goal"),  # too early for JEE
        ({"class_level": "nursery", "goal": "board_exam"}, "goal"),  # no exams in Nursery
        ({"class_level": "class_12", "stream": "commerce", "goal": "neet"}, "goal"),  # NEET needs Science
    ],
)
async def test_choices_that_do_not_fit_the_class_are_rejected(client: AsyncClient, profile, field):
    parent = await register(client)

    response = await client.post(f"{API}/students", json=child_payload(**profile), headers=parent.headers)

    assert response.status_code == 422
    assert error_code(response) == "invalid_learning_profile"
    assert [detail["field"] for detail in response.json()["error"]["details"]] == [field]
    assert (await client.get(f"{API}/students", headers=parent.headers)).json() == []


@pytest.mark.parametrize(
    ("profile", "field"),
    [
        ({"class_level": "class_13"}, "profile.class_level"),
        ({"board": "hogwarts"}, "profile.board"),
        ({"medium": "klingon"}, "profile.medium"),
        ({"primary_language": "ta"}, "profile.primary_language"),  # not switched on yet
        ({"subjects": ["x" * 61]}, "profile.subjects"),
    ],
)
async def test_unknown_values_are_rejected(client: AsyncClient, profile, field):
    parent = await register(client)
    response = await client.post(f"{API}/students", json=child_payload(**profile), headers=parent.headers)
    assert response.status_code == 422
    assert [detail["field"] for detail in response.json()["error"]["details"]] == [field]


async def test_regional_medium_is_accepted_even_before_the_ai_speaks_that_language(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent, medium="mr", primary_language="hi")
    assert child["profile"]["medium"] == "mr"


async def test_age_must_be_sensible(client: AsyncClient):
    parent = await register(client)
    payload = child_payload() | {"age": 40}
    response = await client.post(f"{API}/students", json=payload, headers=parent.headers)
    assert response.status_code == 422


async def test_there_is_a_limit_on_children_per_parent(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_students_per_parent", 2)
    parent = await register(client)
    await add_child(client, parent)
    await add_child(client, parent)

    response = await client.post(f"{API}/students", json=child_payload(), headers=parent.headers)

    assert response.status_code == 409
    assert error_code(response) == "student_limit_reached"


# --------------------------------------------------------------------------- isolation between families


async def test_a_parent_can_never_see_or_touch_another_parents_child(client: AsyncClient):
    sharma = await register(client)
    verma = await register(client)
    sharma_child = await add_child(client, sharma)
    url = f"{API}/students/{sharma_child['id']}"

    assert (await client.get(f"{API}/students", headers=verma.headers)).json() == []

    attempts = [
        await client.get(url, headers=verma.headers),
        await client.patch(url, json={"name": "Hacked"}, headers=verma.headers),
        await client.put(
            f"{url}/profile", json={"class_level": "class_1", "board": "cbse"}, headers=verma.headers
        ),
        await client.delete(url, headers=verma.headers),
        await client.post(f"{url}/session", headers=verma.headers),
    ]
    for response in attempts:
        # 404, not 403: the other family must not even learn that this child exists.
        assert response.status_code == 404, response.request.method
        assert error_code(response) == "student_not_found"

    untouched = (await client.get(url, headers=sharma.headers)).json()
    assert untouched["name"] == "Aarav"
    assert untouched["profile"]["class_level"] == "class_7"


async def test_unknown_student_id_is_404_and_bad_id_is_422(client: AsyncClient):
    parent = await register(client)
    assert (await client.get(f"{API}/students/{uuid.uuid4()}", headers=parent.headers)).status_code == 404
    assert (await client.get(f"{API}/students/not-a-uuid", headers=parent.headers)).status_code == 422


async def test_children_endpoints_need_a_signed_in_user(client: AsyncClient):
    assert (await client.get(f"{API}/students")).status_code == 401
    assert (await client.post(f"{API}/students", json=child_payload())).status_code == 401


# --------------------------------------------------------------------------- students who signed up alone


async def test_self_registered_student_finishes_onboarding(client: AsyncClient):
    student = await register(client, role="student", full_name="Kabir Verma")
    me = (await client.get(f"{API}/auth/me", headers=student.headers)).json()
    student_id = me["active_student"]["id"]

    response = await client.put(
        f"{API}/students/{student_id}/profile",
        json={"class_level": "class_12", "board": "cbse", "stream": "science", "goal": "neet"},
        headers=student.headers,
    )

    assert response.status_code == 200
    assert response.json()["profile"]["goal"] == "neet"
    me = (await client.get(f"{API}/auth/me", headers=student.headers)).json()
    assert me["onboarding_complete"] is True
    assert [s["id"] for s in (await client.get(f"{API}/students", headers=student.headers)).json()] == [
        student_id
    ]


async def test_self_registered_student_cannot_use_parent_features(client: AsyncClient):
    student = await register(client, role="student")
    student_id = (await client.get(f"{API}/auth/me", headers=student.headers)).json()["active_student"]["id"]

    add = await client.post(f"{API}/students", json=child_payload(), headers=student.headers)
    remove = await client.delete(f"{API}/students/{student_id}", headers=student.headers)
    session = await client.post(f"{API}/students/{student_id}/session", headers=student.headers)

    for response in (add, remove, session):
        assert response.status_code == 403
        assert error_code(response) == "parent_required"


async def test_self_registered_student_cannot_see_a_parents_child(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    student = await register(client, role="student")

    response = await client.get(f"{API}/students/{child['id']}", headers=student.headers)
    assert response.status_code == 404

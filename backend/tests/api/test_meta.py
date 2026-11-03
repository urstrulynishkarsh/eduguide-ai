"""Form options and class profiles (public)."""

from httpx import AsyncClient

from tests.api.helpers import API


async def test_onboarding_options_need_no_login(client: AsyncClient):
    response = await client.get(f"{API}/meta/options")

    assert response.status_code == 200
    body = response.json()
    assert [item["label"] for item in body["classes"]][:4] == ["Nursery", "LKG", "UKG", "Class 1"]
    assert len(body["classes"]) == 15
    assert [item["code"] for item in body["boards"]] == ["cbse", "icse", "state", "other"]
    assert [item["code"] for item in body["streams"]] == ["science", "commerce", "arts"]
    assert [item["code"] for item in body["languages"]] == ["en", "hi", "hinglish"]
    mediums = [item["code"] for item in body["mediums"]]
    assert "hinglish" not in mediums
    assert {"en", "hi", "mr", "ta", "other"} <= set(mediums)


async def test_options_tell_the_form_which_rules_depend_on_the_class(client: AsyncClient):
    classes = {
        item["class_level"]: item for item in (await client.get(f"{API}/meta/options")).json()["classes"]
    }

    assert classes["class_7"]["requires_stream"] is False
    assert "jee" not in classes["class_7"]["available_goals"]
    assert classes["class_12"]["requires_stream"] is True
    assert {"jee", "neet", "cuet"} <= set(classes["class_12"]["available_goals"])
    assert "Physics" in classes["class_12"]["suggested_subjects_by_stream"]["science"]
    assert classes["nursery"]["ui_mode"] == "playful"
    assert classes["class_10"]["ui_mode"] == "dense"


async def test_full_class_profile(client: AsyncClient):
    response = await client.get(f"{API}/meta/classes/class_5")

    assert response.status_code == 200
    profile = response.json()
    assert profile["class_level"] == "class_5"
    assert profile["age_range"] == "9-11"
    assert profile["language_complexity"] == "simple"
    assert profile["question_complexity"] == "medium"
    assert profile["explanation_style"] == "child_friendly"
    assert profile["max_concept_depth"] == "intermediate"
    assert profile["features"]["practice_tests"] is True
    assert profile["ai_guidelines"]


async def test_unknown_class_is_rejected(client: AsyncClient):
    response = await client.get(f"{API}/meta/classes/class_13")
    assert response.status_code == 422

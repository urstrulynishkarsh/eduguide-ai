"""Settings refuse to start in an unsafe state. No database needed."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD_SECRET = "s" * 48


def _settings(**values):
    return Settings(_env_file=None, **values)


def test_a_missing_secret_stops_the_app_with_a_helpful_message(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError) as error:
        _settings()
    assert "python -m scripts.init_env" in str(error.value)


def test_a_short_secret_is_rejected(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        _settings(jwt_secret_key="too-short")


def test_cors_origins_are_split_on_commas():
    settings = _settings(
        jwt_secret_key=GOOD_SECRET, cors_origins="http://localhost:3000, https://app.example.com ,"
    )
    assert settings.cors_origin_list == ["http://localhost:3000", "https://app.example.com"]


def test_production_refuses_wildcard_cors():
    with pytest.raises(ValidationError):
        _settings(jwt_secret_key=GOOD_SECRET, environment="production", cors_origins="*")


def test_production_refuses_sql_echo():
    with pytest.raises(ValidationError):
        _settings(jwt_secret_key=GOOD_SECRET, environment="production", db_echo=True)

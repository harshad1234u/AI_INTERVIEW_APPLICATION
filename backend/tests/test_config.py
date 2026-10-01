import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("API_PORT", "9001")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://app.example.com")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    s = Settings(_env_file=None)

    assert s.database_url == "postgresql+psycopg://u:p@db:5432/x"
    assert s.api_port == 9001
    assert s.environment == "development"
    assert s.cors_origin_list == ["http://localhost:3000", "https://app.example.com"]


def test_missing_database_url_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_invalid_environment_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("ENVIRONMENT", "staging-ish")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_wildcard_cors_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        _ = Settings(_env_file=None).cors_origin_list

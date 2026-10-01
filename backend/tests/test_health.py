from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_health_ok_against_real_database() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


class _BrokenSession:
    def execute(self, *_: object) -> None:
        raise OperationalError(
            "SELECT 1", {}, Exception("password authentication failed for user secret_user")
        )


def _broken_db() -> Iterator[_BrokenSession]:
    yield _BrokenSession()


def test_health_database_down_returns_503_without_leaking_details() -> None:
    app.dependency_overrides[get_db] = _broken_db
    try:
        res = client.get("/api/health")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert res.json() == {"status": "degraded", "database": "unavailable"}
    assert "secret_user" not in res.text


def test_cors_allows_configured_origin_only() -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"

    evil = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in evil.headers


def test_unknown_route_is_json_404() -> None:
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.json() == {"detail": "Not Found"}

import logging
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.candidates import _commit
from app.core.config import Settings
from app.main import app, create_app
from app.models import Candidate

EMAIL = "harshad@example.com"


def create(client: TestClient, email: str = EMAIL, name: str = "Harshad") -> dict:
    res = client.post("/api/candidates", json={"email": email, "name": name})
    assert res.status_code == 201, res.text
    return res.json()


# ---------- create ----------


def test_create_returns_201_and_normalizes(client: TestClient) -> None:
    res = client.post(
        "/api/candidates", json={"email": "  Harshad@Example.COM ", "name": "  Harshad \t  Ambi "}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == EMAIL
    assert body["name"] == "Harshad Ambi"
    uuid.UUID(body["id"])
    assert body["created_at"]
    assert set(body) == {"id", "email", "name", "created_at"}


@pytest.mark.parametrize(
    "payload",
    [
        {"email": EMAIL},
        {"name": "Harshad"},
        {"email": EMAIL, "name": ""},
        {"email": EMAIL, "name": "   \t "},
        {"email": EMAIL, "name": "x" * 201},
        {"email": EMAIL, "name": None},
        {"email": "not-an-email", "name": "Harshad"},
        {"email": "a@b", "name": "Harshad"},
        {"email": "a@@example.com", "name": "Harshad"},
        {"email": "", "name": "Harshad"},
        {"email": "a" * 250 + "@example.com", "name": "Harshad"},
    ],
    ids=[
        "missing-name", "missing-email", "empty-name", "blank-name", "long-name", "null-name",
        "no-at", "no-dot-domain", "double-at", "empty-email", "long-email",
    ],
)
def test_create_rejects_invalid_input(client: TestClient, payload: dict) -> None:
    assert client.post("/api/candidates", json=payload).status_code == 422


def test_create_accepts_max_length_name(client: TestClient) -> None:
    assert create(client, name="x" * 200)["name"] == "x" * 200


@pytest.mark.parametrize(
    "extra", [{"id": str(uuid.uuid4())}, {"created_at": "2020-01-01T00:00:00Z"}]
)
def test_create_rejects_server_controlled_fields(client: TestClient, extra: dict) -> None:
    res = client.post("/api/candidates", json={"email": EMAIL, "name": "H", **extra})
    assert res.status_code == 422


@pytest.mark.parametrize("dupe", [EMAIL, "HARSHAD@EXAMPLE.COM"])
def test_create_duplicate_email_is_409(client: TestClient, dupe: str) -> None:
    create(client)
    res = client.post("/api/candidates", json={"email": dupe, "name": "Other"})
    assert res.status_code == 409
    assert res.json() == {"detail": "A candidate with this email already exists"}


# ---------- read ----------


def test_read_existing(client: TestClient) -> None:
    created = create(client)
    res = client.get(f"/api/candidates/{created['id']}")
    assert res.status_code == 200
    assert res.json() == created


def test_read_nonexistent_is_404(client: TestClient) -> None:
    res = client.get(f"/api/candidates/{uuid.uuid4()}")
    assert res.status_code == 404
    assert res.json() == {"detail": "Candidate not found"}


def test_read_malformed_id_is_422(client: TestClient) -> None:
    assert client.get("/api/candidates/not-a-uuid").status_code == 422


def test_no_list_endpoint(client: TestClient) -> None:
    assert client.get("/api/candidates").status_code == 405


# ---------- update ----------


def test_update_name_only_leaves_email(client: TestClient) -> None:
    c = create(client)
    res = client.patch(f"/api/candidates/{c['id']}", json={"name": "  New   Name "})
    assert res.status_code == 200
    assert res.json() == {**c, "name": "New Name"}


def test_update_email_only_normalizes_and_leaves_name(client: TestClient) -> None:
    c = create(client)
    res = client.patch(f"/api/candidates/{c['id']}", json={"email": "New@Example.com"})
    assert res.status_code == 200
    assert res.json() == {**c, "email": "new@example.com"}
    assert client.get(f"/api/candidates/{c['id']}").json()["email"] == "new@example.com"


def test_update_both_fields(client: TestClient) -> None:
    c = create(client)
    res = client.patch(
        f"/api/candidates/{c['id']}", json={"email": "b@example.com", "name": "B"}
    )
    assert res.json() == {**c, "email": "b@example.com", "name": "B"}


def test_update_to_own_email_is_ok(client: TestClient) -> None:
    c = create(client)
    assert client.patch(f"/api/candidates/{c['id']}", json={"email": EMAIL}).status_code == 200


def test_update_to_taken_email_is_409_and_rolls_back(client: TestClient) -> None:
    create(client, email="taken@example.com")
    c = create(client)
    res = client.patch(
        f"/api/candidates/{c['id']}", json={"email": "Taken@example.com", "name": "Changed"}
    )
    assert res.status_code == 409
    assert client.get(f"/api/candidates/{c['id']}").json() == c


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"email": None},
        {"name": "   "},
        {"email": "bad"},
        {"id": str(uuid.uuid4())},
        {"created_at": "2020-01-01T00:00:00Z"},
        {"name": "Ok", "id": str(uuid.uuid4())},
    ],
    ids=["empty", "null-name", "null-email", "blank-name", "bad-email", "id", "created_at", "mixed"],
)
def test_update_rejects_invalid_patch(client: TestClient, payload: dict) -> None:
    c = create(client)
    assert client.patch(f"/api/candidates/{c['id']}", json=payload).status_code == 422
    assert client.get(f"/api/candidates/{c['id']}").json() == c


def test_update_nonexistent_is_404(client: TestClient) -> None:
    res = client.patch(f"/api/candidates/{uuid.uuid4()}", json={"name": "X"})
    assert res.status_code == 404


# ---------- delete ----------


def test_delete_removes_candidate(client: TestClient, db_session: Session) -> None:
    c = create(client)
    res = client.delete(f"/api/candidates/{c['id']}")
    assert res.status_code == 204
    assert res.content == b""
    assert client.get(f"/api/candidates/{c['id']}").status_code == 404
    assert db_session.scalar(select(Candidate).where(Candidate.email == EMAIL)) is None
    assert client.delete(f"/api/candidates/{c['id']}").status_code == 404


def test_delete_frees_email_for_reuse(client: TestClient) -> None:
    c = create(client)
    client.delete(f"/api/candidates/{c['id']}")
    create(client)


def test_delete_nonexistent_is_404(client: TestClient) -> None:
    assert client.delete(f"/api/candidates/{uuid.uuid4()}").status_code == 404


# ---------- database unavailable / privacy ----------


def test_database_unavailable_is_controlled_503(
    dead_database_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    for res in (
        dead_database_client.post("/api/candidates", json={"email": EMAIL, "name": "H"}),
        dead_database_client.get(f"/api/candidates/{uuid.uuid4()}"),
    ):
        assert res.status_code == 503
        assert res.json() == {"detail": "Service temporarily unavailable. Please try again."}
        for leak in ("secretpw", "127.0.0.1", "nobody", "psycopg"):
            assert leak not in res.text
    assert "secretpw" not in caplog.text
    assert EMAIL not in caplog.text


def test_duplicate_does_not_log_personal_data(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    create(client)
    client.post("/api/candidates", json={"email": EMAIL, "name": "Harshad"})
    assert EMAIL not in caplog.text
    assert "Harshad" not in caplog.text


def test_unexpected_constraint_violation_is_500_without_personal_data(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    # Bypass schema validation to hit a DB CHECK the API normally prevents.
    db_session.add(Candidate(email="Upper@Example.com", name="Secret Person"))
    caplog.set_level(logging.DEBUG)
    with pytest.raises(HTTPException) as exc:
        _commit(db_session)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Could not save candidate"
    assert "ck_candidates_email_lowercase" in caplog.text
    assert "Upper@Example.com" not in caplog.text
    assert "Secret Person" not in caplog.text


def test_candidate_routes_not_served_in_production() -> None:
    prod = create_app(
        Settings(_env_file=None, database_url="postgresql+psycopg://u:p@h/x", environment="production")
    )
    c = TestClient(prod)
    assert c.post("/api/candidates", json={"email": EMAIL, "name": "H"}).status_code == 404
    assert c.get(f"/api/candidates/{uuid.uuid4()}").status_code == 404
    # Control: the same request is routed outside production.
    assert TestClient(app).get("/api/candidates/not-a-uuid").status_code == 422

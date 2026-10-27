"""Phase 12: authentication, sessions, lockout, CSRF, and candidate isolation (IDOR)."""

import base64
import hashlib
import logging
import threading
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.ai.providers import get_model_gateway
from app.api.deps import SESSION_COOKIE, current_candidate
from app.api.routes import (
    auth as auth_routes,
    candidates,
    health,
    interview_sessions,
    manual_facts,
    resumes,
)
from app.core import security
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.main import app, create_app
from app.models import AuthSession, Candidate
from app.models.resume import FactCategory as FC, FactStatus
from app.services import auth
from tests.auth_helpers import api_client, make_candidate
from tests.test_evaluation_api import evaluate
from tests.test_interview_plan_api import SETTINGS, add_facts
from tests.test_interview_turn_api import act, ans, nxt
from tests.test_report import post_report

PASSWORD = "correct horse 1"
EMAIL = "asha@example.com"
BAD_CREDENTIALS = {"detail": "Email or password is incorrect."}
LOCKED = {"detail": "Too many failed attempts. Please try again in 15 minutes."}
NOT_AUTHENTICATED = {"detail": "Please log in."}


def register(client: TestClient, email: str = EMAIL, password: str = PASSWORD,
             name: str = "Asha Rao"):
    return client.post("/api/auth/register",
                       json={"email": email, "name": name, "password": password})


def login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def me(client: TestClient):
    return client.get("/api/auth/me")


def token_of(client: TestClient) -> str:
    return client.cookies[SESSION_COOKIE]


# ---------- unit: passwords ----------


def test_password_hash_verifies_only_the_right_password() -> None:
    stored = security.hash_password(PASSWORD)
    assert stored.startswith("scrypt$16384$8$5$")
    assert PASSWORD not in stored
    assert security.verify_password(PASSWORD, stored)
    for wrong in ("correct horse 2", "", PASSWORD.upper(), PASSWORD + " ", "ünïcødé"):
        assert not security.verify_password(wrong, stored)


def test_every_hash_has_its_own_salt() -> None:
    first, second = security.hash_password(PASSWORD), security.hash_password(PASSWORD)
    assert first != second
    assert first.split("$")[4] != second.split("$")[4]
    assert security.verify_password(PASSWORD, first) and security.verify_password(PASSWORD, second)


def test_non_ascii_passwords_round_trip() -> None:
    password = "pässwörd ✓ 密码"
    assert security.verify_password(password, security.hash_password(password))


@pytest.mark.parametrize("stored", [
    "", "scrypt", "plaintext-password", "bcrypt$16384$8$5$c2FsdA==$a2V5",
    "scrypt$16384$8$5$!!notbase64$a2V5", "scrypt$x$8$5$c2FsdA==$a2V5",
    "scrypt$16384$8$5$c2FsdA==", "scrypt$3$8$5$c2FsdA==$a2V5",  # n must be a power of two
    "scrypt$1073741824$8$5$c2FsdA==$a2V5",  # beyond maxmem
])
def test_a_malformed_stored_hash_verifies_nothing_and_never_raises(stored: str) -> None:
    assert security.verify_password(PASSWORD, stored) is False


def test_a_stored_hash_keeps_its_own_parameters() -> None:
    """Raising the cost later must not lock out existing passwords."""
    salt = b"0123456789abcdef"
    key = hashlib.scrypt(PASSWORD.encode(), salt=salt, n=2**4, r=8, p=1, dklen=32)
    stored = f"scrypt$16$8$1${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"
    assert security.verify_password(PASSWORD, stored)
    assert not security.verify_password("nope", stored)


# ---------- unit: tokens ----------


def test_session_tokens_are_random_and_stored_only_as_sha256() -> None:
    tokens = {security.new_session_token() for _ in range(200)}
    assert len(tokens) == 200
    token = tokens.pop()
    assert len(token) >= 43  # 32 random bytes, URL-safe base64
    assert security.token_hash(token) == hashlib.sha256(token.encode()).hexdigest()
    assert security.token_hash(token) != token and len(security.token_hash(token)) == 64


def test_start_session_stores_the_hash_and_drops_expired_sessions(db_session: Session) -> None:
    candidate = Candidate(email=EMAIL, name="A")
    db_session.add(candidate)
    db_session.flush()
    old = auth.start_session(db_session, candidate.id)
    db_session.execute(update(AuthSession).values(
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        created_at=datetime.now(UTC) - timedelta(days=8)))
    assert auth.session_candidate(db_session, old) is None  # expired: unauthenticated
    new = auth.start_session(db_session, candidate.id)
    hashes = db_session.scalars(select(AuthSession.token_hash)).all()
    assert hashes == [security.token_hash(new)]  # the expired one was cleaned up
    assert auth.session_candidate(db_session, new).id == candidate.id
    session = db_session.scalar(select(AuthSession))
    assert session.expires_at - session.created_at == auth.SESSION_TTL


# ---------- unit: lockout ----------


@pytest.fixture
def with_password(db_session: Session) -> Candidate:
    candidate = Candidate(email=EMAIL, name="A", password_hash=security.hash_password(PASSWORD))
    db_session.add(candidate)
    db_session.flush()
    return candidate


def test_failures_count_up_to_a_lock_and_success_resets(
    db_session: Session, with_password: Candidate
) -> None:
    for expected in range(1, auth.MAX_FAILED_LOGINS):
        with pytest.raises(auth.InvalidCredentials):
            auth.authenticate(db_session, EMAIL, "wrong")
        assert (with_password.failed_logins, with_password.locked_until) == (expected, None)
    assert auth.authenticate(db_session, EMAIL, PASSWORD) is with_password
    assert (with_password.failed_logins, with_password.locked_until) == (0, None)

    before = datetime.now(UTC)
    for _ in range(auth.MAX_FAILED_LOGINS):
        with pytest.raises(auth.InvalidCredentials):
            auth.authenticate(db_session, EMAIL, "wrong")
    assert with_password.failed_logins == 0  # the lock replaces the count
    assert before + auth.LOCKOUT <= with_password.locked_until <= datetime.now(UTC) + auth.LOCKOUT
    with pytest.raises(auth.AccountLocked):  # even with the right password
        auth.authenticate(db_session, EMAIL, PASSWORD)


def test_an_expired_lock_lets_the_right_password_in(
    db_session: Session, with_password: Candidate
) -> None:
    with_password.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    with_password.failed_logins = 3
    assert auth.authenticate(db_session, EMAIL, PASSWORD) is with_password
    assert (with_password.failed_logins, with_password.locked_until) == (0, None)


def test_unknown_email_and_no_password_are_plain_invalid_credentials(db_session: Session) -> None:
    db_session.add(Candidate(email="legacy@example.com", name="L"))  # A3: pre-auth profile
    db_session.flush()
    for email in ("nobody@example.com", "legacy@example.com"):
        with pytest.raises(auth.InvalidCredentials):
            auth.authenticate(db_session, email, PASSWORD)


# ---------- API: register / login / logout / me ----------


def test_register_signs_in_and_never_returns_secrets(
    client: TestClient, db_session: Session
) -> None:
    res = register(client, email="  Asha@Example.COM ")
    assert res.status_code == 201
    body = res.json()
    assert set(body) == {"id", "email", "name", "created_at"} and body["email"] == EMAIL
    token = token_of(client)
    assert token not in res.text and PASSWORD not in res.text
    stored = db_session.scalar(select(Candidate.password_hash).where(Candidate.email == EMAIL))
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert db_session.scalars(select(AuthSession.token_hash)).all() == [security.token_hash(token)]
    assert me(client).json() == body


def test_session_cookie_flags(client: TestClient) -> None:
    cookie = register(client).headers["set-cookie"]
    parts = {p.strip().split("=")[0].lower() for p in cookie.split(";")}
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert {"httponly", "path", "max-age", "samesite"} <= parts
    assert "samesite=lax" in cookie.lower() and "Max-Age=604800" in cookie and "Path=/" in cookie
    assert "secure" not in parts  # plain-HTTP development default


def test_cookie_is_secure_when_configured(client: TestClient) -> None:
    secure = get_settings().model_copy(update={"auth_cookie_secure": True})
    app.dependency_overrides[get_settings] = lambda: secure
    try:
        assert "secure" in register(client).headers["set-cookie"].lower().split("; ")
        assert "secure" in client.post("/api/auth/logout").headers["set-cookie"].lower().split("; ")
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.parametrize("password", ["Zq9!xY", "x" * 129, "", None, 12345678])
def test_register_rejects_bad_passwords_without_echoing_them(
    client: TestClient, db_session: Session, password: object
) -> None:
    res = client.post("/api/auth/register",
                      json={"email": EMAIL, "name": "A", "password": password})
    assert res.status_code == 422
    if isinstance(password, str) and password:
        assert password not in res.text
    assert db_session.scalar(select(Candidate)) is None


def test_validation_errors_on_auth_routes_never_echo_the_body(client: TestClient) -> None:
    secret = "my secret password"
    for res in (client.post("/api/auth/register", json={"email": EMAIL, "password": secret}),
                client.post("/api/auth/login", json={"email": "not-an-email", "password": secret})):
        assert res.status_code == 422 and secret not in res.text
        assert all("input" not in e for e in res.json()["detail"])


def test_a_password_that_is_not_valid_unicode_is_422(client: TestClient) -> None:
    body = '{"email": "a@example.com", "name": "A", "password": "\\ud800abcdefgh"}'
    res = client.post("/api/auth/register", content=body,
                      headers={"Content-Type": "application/json"})
    assert res.status_code == 422


def test_duplicate_registration_is_409_and_keeps_the_first(
    client: TestClient, db_session: Session
) -> None:
    first = register(client).json()
    other = api_client()
    res = register(other, email="ASHA@example.com", password="another password")
    assert (res.status_code, res.json()) == (
        409, {"detail": "A candidate with this email already exists"})
    assert SESSION_COOKIE not in other.cookies
    assert login(api_client()).json() == first  # the first password still works
    assert login(api_client(), password="another password").status_code == 401


def test_login_and_logout(client: TestClient, db_session: Session) -> None:
    created = register(client).json()
    browser = api_client()
    res = login(browser, email="ASHA@EXAMPLE.COM")
    assert (res.status_code, res.json()) == (200, created)
    assert "httponly" in res.headers["set-cookie"].lower()
    assert token_of(browser) != token_of(client)  # each sign-in is its own session
    assert db_session.scalar(select(text("count(*)")).select_from(AuthSession)) == 2

    res = browser.post("/api/auth/logout")
    assert (res.status_code, res.content) == (204, b"")
    assert f'{SESSION_COOKIE}=""' in res.headers["set-cookie"]
    assert me(browser).status_code == 401
    assert me(client).status_code == 200  # logout ends only that session
    assert browser.post("/api/auth/logout").status_code == 204  # idempotent


def test_a_logged_out_token_stays_dead_even_if_replayed(client: TestClient) -> None:
    register(client)
    token = token_of(client)
    client.post("/api/auth/logout")
    replay = api_client(token)
    assert (me(replay).status_code, me(replay).json()) == (401, NOT_AUTHENTICATED)


@pytest.mark.parametrize("case", ["wrong-password", "unknown-email", "no-password-set"])
def test_failed_logins_are_indistinguishable(
    client: TestClient, db_session: Session, case: str
) -> None:
    register(api_client())
    db_session.add(Candidate(email="legacy@example.com", name="L"))  # A3
    db_session.flush()
    email, password = {"wrong-password": (EMAIL, "wrong password"),
                       "unknown-email": ("nobody@example.com", PASSWORD),
                       "no-password-set": ("legacy@example.com", PASSWORD)}[case]
    res = login(client, email=email, password=password)
    assert (res.status_code, res.json()) == (401, BAD_CREDENTIALS)
    assert "set-cookie" not in res.headers


def test_legacy_candidates_cannot_log_in_or_be_claimed(
    client: TestClient, db_session: Session
) -> None:
    db_session.add(Candidate(email="legacy@example.com", name="L"))
    db_session.flush()
    assert login(client, email="legacy@example.com").status_code == 401
    assert register(client, email="legacy@example.com").status_code == 409
    assert db_session.scalar(select(Candidate.password_hash)) is None


def test_lockout_through_the_api(client: TestClient, db_session: Session) -> None:
    register(api_client())
    for _ in range(auth.MAX_FAILED_LOGINS):
        assert login(client, password="wrong password").json() == BAD_CREDENTIALS
    res = login(client)  # right password, but locked
    assert (res.status_code, res.json()) == (429, LOCKED)
    assert "set-cookie" not in res.headers
    db_session.execute(update(Candidate).values(
        locked_until=datetime.now(UTC) - timedelta(seconds=1)))
    assert login(client).status_code == 200
    assert db_session.scalar(select(Candidate.failed_logins)) == 0


def test_me_without_a_valid_session_is_401(client: TestClient, db_session: Session) -> None:
    assert (me(client).status_code, me(client).json()) == (401, NOT_AUTHENTICATED)
    assert me(api_client("not-a-real-token")).status_code == 401
    register(client)
    db_session.execute(update(AuthSession).values(
        created_at=datetime.now(UTC) - timedelta(days=8),
        expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    assert me(client).status_code == 401  # expired: as good as none


def test_me_reflects_profile_changes(client: TestClient) -> None:
    cid = register(client).json()["id"]
    client.patch(f"/api/candidates/{cid}", json={"email": "new@example.com"})
    assert me(client).json()["email"] == "new@example.com"
    assert login(api_client(), email="new@example.com").status_code == 200


def test_auth_never_logs_secrets_or_personal_data(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    register(client)
    token = token_of(client)
    login(api_client(), password="wrong password")
    login(api_client())
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"email": EMAIL, "name": "A", "password": "short"})
    for secret in (PASSWORD, "wrong password", token, security.token_hash(token), EMAIL, "Asha"):
        assert secret not in caplog.text


def test_auth_routes_cannot_reach_a_model() -> None:
    auth_routes = [r for _, p, r in _routes() if p.startswith("/api/auth/")]
    assert len(auth_routes) == 4
    assert not any(_depends_on(r.dependant, get_model_gateway) for r in auth_routes)


def test_auth_database_unavailable_is_503(dead_database_client: TestClient) -> None:
    for res in (register(dead_database_client), login(dead_database_client),
                me(dead_database_client), dead_database_client.post("/api/auth/logout")):
        assert res.status_code == 503
        assert res.json() == {"detail": "Service temporarily unavailable. Please try again."}


# ---------- CSRF: Origin check (A5) ----------


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null", "http://localhost:3001",
                                    "http://localhost:3000.evil.example"])
def test_state_changing_requests_need_an_allowed_origin(
    client: TestClient, db_session: Session, origin: str | None
) -> None:
    register(client)
    cid = me(client).json()["id"]
    before = db_session.scalar(select(Candidate.name))
    headers = {"Origin": origin} if origin else {}
    hostile = api_client(token_of(client))
    if origin is None:
        del hostile.headers["Origin"]
    for res in (hostile.patch(f"/api/candidates/{cid}", json={"name": "Hacked"}, headers=headers),
                hostile.delete(f"/api/candidates/{cid}", headers=headers),
                hostile.post("/api/auth/logout", headers=headers),
                hostile.put(f"/api/interview-sessions/{uuid.uuid4()}/ai-consent",
                            json={"granted": True}, headers=headers),
                hostile.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD},
                             headers=headers)):
        assert (res.status_code, res.json()) == (403, {"detail": "Request origin not allowed."})
    assert db_session.scalar(select(Candidate.name)) == before
    assert me(client).status_code == 200  # the logout was refused too


def test_safe_methods_need_no_origin(client: TestClient) -> None:
    register(client)
    plain = api_client(token_of(client))
    del plain.headers["Origin"]
    assert me(plain).status_code == 200
    assert plain.get("/api/health").status_code == 200
    assert plain.head("/api/health").status_code in (200, 405)


def test_cors_preflight_and_credentials(client: TestClient) -> None:
    plain = TestClient(app)
    ok = plain.options("/api/auth/login", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert ok.headers["access-control-allow-credentials"] == "true"
    bad = plain.options("/api/auth/login", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert bad.status_code == 400 and "access-control-allow-origin" not in bad.headers
    res = register(client)
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert res.headers["access-control-allow-credentials"] == "true"


# ---------- 401 sweep: every route needs a session unless it is deliberately public ----------

PUBLIC = {("GET", "/api/health"), ("POST", "/api/auth/register"), ("POST", "/api/auth/login"),
          ("POST", "/api/auth/logout")}


ROUTERS = [health.router, auth_routes.router, candidates.router, resumes.router,
           manual_facts.router, interview_sessions.router]


def _routes() -> list[tuple[str, str, APIRoute]]:
    return [(method, "/api" + r.path, r) for router in ROUTERS for r in router.routes
            if isinstance(r, APIRoute) for method in sorted(r.methods - {"HEAD"})]


def _served(application) -> set[tuple[str, str]]:
    return {(m.upper(), path) for path, ops in application.openapi()["paths"].items()
            for m in ops}


def test_the_sweep_covers_every_served_route() -> None:
    """A router added to the app but not to ROUTERS fails here, so the sweep cannot miss it."""
    assert _served(app) == {(m, p) for m, p, _ in _routes()}


def _depends_on(dependant, target: Callable) -> bool:
    return any(d.call is target or _depends_on(d, target) for d in dependant.dependencies)


def test_every_non_public_route_depends_on_the_signed_in_candidate() -> None:
    """Structural: a new route added without authentication fails here."""
    routes = _routes()
    assert {(m, p) for m, p, _ in routes} >= PUBLIC
    unprotected = {(m, p) for m, p, r in routes if not _depends_on(r.dependant, current_candidate)}
    assert unprotected == PUBLIC


@pytest.mark.parametrize("token", [None, "forged-token"], ids=["no-cookie", "unknown-session"])
def test_every_protected_route_rejects_unauthenticated_requests(
    client: TestClient, db_session: Session, token: str | None
) -> None:
    """Behavioural: called with real-looking ids and bodies, each one answers 401."""
    if token:
        client.cookies.set(SESSION_COOKIE, token)
    checked = 0
    for method, path, _ in _routes():
        if (method, path) in PUBLIC:
            continue
        url = path
        for param in ("candidate_id", "resume_id", "session_id", "fact_id", "question_id"):
            url = url.replace("{" + param + "}", str(uuid.uuid4()))
        res = client.request(method, url, json={})
        assert (res.status_code, res.json()) == (401, NOT_AUTHENTICATED), (method, path)
        checked += 1
    assert checked >= 25
    assert db_session.scalar(select(text("count(*)")).select_from(Candidate)) == 0


def test_the_upload_rejects_an_unauthenticated_file(client: TestClient) -> None:
    res = client.post("/api/resumes", files={"file": ("r.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert res.status_code == 401


def test_production_still_serves_only_the_health_check() -> None:  # A7
    prod_app = create_app(Settings(_env_file=None, database_url="postgresql+psycopg://u:p@h/x",
                                   environment="production"))
    assert _served(prod_app) == {("GET", "/api/health")}
    prod = TestClient(prod_app, headers={"Origin": "http://localhost:3000"})
    assert prod.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
                     ).status_code == 404


# ---------- IDOR matrix: two candidates, every resource ----------


def build_world(client: TestClient, db: Session, email: str) -> dict:
    """A signed-in candidate with a reviewed resume, a COMPLETED interview with an evaluated answer
    and its report, and a second session just created (PROFILE_REVIEW)."""
    cid = make_candidate(client, db, email, email.split("@")[0])
    fact_ids = add_facts(db, cid, (FC.PROJECT, "TrustLens", FactStatus.APPROVED),
                         (FC.SKILL, "React", FactStatus.APPROVED))
    resume_id = db.scalar(text("SELECT resume_id FROM candidate_facts WHERE id = :f"),
                          {"f": fact_ids[0]})
    done = client.post("/api/interview-sessions", json={}).json()["id"]
    assert act(client, done, "CONFIRM_PROFILE").status_code == 200
    assert client.post(f"/api/interview-sessions/{done}/plan", json=SETTINGS).status_code == 200
    assert act(client, done, "START_INTERVIEW").status_code == 200
    question = nxt(client, done).json()["question"]
    assert ans(client, done, question["id"], said="I would explain the design.").status_code == 200
    nxt(client, done)
    assert act(client, done, "END_INTERVIEW").json()["status"] == "REPORT_GENERATION"
    assert evaluate(client, done, question["id"]).status_code == 200
    assert post_report(client, done).json()["status"] == "COMPLETED"
    live = client.post("/api/interview-sessions", json={}).json()["id"]
    manual = client.post(f"/api/candidates/{cid}/manual-facts",  # Phase 13
                         json={"category": "SKILL", "fact": "Go"}).json()["id"]
    return {"candidate": cid, "resume": str(resume_id), "fact": str(fact_ids[0]), "done": done,
            "question": question["id"], "live": live, "manual": manual}


def intruder_requests(w: dict, mine: dict) -> list[tuple[str, str, dict | None]]:
    """Every way to reach world w's data. `mine` = the intruder's own world, for requests that
    put a foreign child id under the intruder's own resource."""
    s, done, live = "/api/interview-sessions", w["done"], w["live"]
    return [
        ("GET", f"/api/candidates/{w['candidate']}", None),
        ("PATCH", f"/api/candidates/{w['candidate']}", {"email": "stolen@example.com"}),
        ("DELETE", f"/api/candidates/{w['candidate']}", None),
        ("GET", f"/api/candidates/{w['candidate']}/resumes", None),
        ("GET", f"/api/candidates/{w['candidate']}/interview-sessions", None),
        ("GET", f"/api/resumes/{w['resume']}", None),
        ("GET", f"/api/resumes/{w['resume']}/facts", None),
        ("PATCH", f"/api/resumes/{w['resume']}/facts/{w['fact']}", {"status": "REJECTED"}),
        ("PATCH", f"/api/resumes/{mine['resume']}/facts/{w['fact']}", {"status": "REJECTED"}),
        ("POST", f"/api/resumes/{w['resume']}/ai-extraction", None),
        ("POST", f"/api/resumes/{w['resume']}/facts/review-pending", {"status": "APPROVED"}),
        ("GET", f"/api/candidates/{w['candidate']}/manual-facts", None),
        ("POST", f"/api/candidates/{w['candidate']}/manual-facts",
         {"category": "SKILL", "fact": "Injected"}),
        ("PATCH", f"/api/manual-facts/{w['manual']}", {"fact": "Hijacked"}),
        ("DELETE", f"/api/manual-facts/{w['manual']}", None),
        ("DELETE", f"/api/resumes/{w['resume']}", None),
        ("GET", f"{s}/{done}", None),
        ("GET", f"{s}/{done}/plan", None),
        ("GET", f"{s}/{done}/questions", None),
        ("GET", f"{s}/{done}/evaluations", None),
        ("GET", f"{s}/{done}/report", None),
        ("GET", f"{s}/{done}/ai-consent", None),
        ("POST", f"{s}/{done}/report", {}),
        ("POST", f"{s}/{done}/retry", {}),
        ("POST", f"{s}/{done}/questions/{w['question']}/evaluation", {}),
        ("POST", f"{s}/{mine['done']}/questions/{w['question']}/evaluation", {}),
        ("PUT", f"{s}/{live}/questions/{w['question']}/expressions", {"status": "UNAVAILABLE"}),
        ("PUT", f"{s}/{live}/ai-consent", {"granted": True}),
        ("POST", f"{s}/{live}/actions", {"action": "CONFIRM_PROFILE"}),
        ("POST", f"{s}/{live}/plan", SETTINGS),
        ("POST", f"{s}/{live}/questions/next", {}),
        ("POST", f"{s}/{live}/answers",
         {"question_id": w["question"], "kind": "ANSWER", "text": "hijack"}),
        ("POST", f"{s}/{mine['live']}/answers",
         {"question_id": w["question"], "kind": "ANSWER", "text": "hijack"}),
        ("DELETE", f"{s}/{live}", None),
        ("DELETE", f"{s}/{done}", None),
    ]


def snapshot(db: Session) -> dict:
    tables = ["candidates", "auth_sessions", "resumes", "candidate_facts", "interview_sessions",
              "interview_consent_events", "interview_questions", "answer_evaluations",
              "answer_evaluation_criteria", "provider_calls"]
    return {t: db.scalars(text(f"SELECT row_to_json(x)::text FROM {t} x ORDER BY 1")).all()
            for t in tables}


@pytest.fixture
def worlds(client: TestClient, db_session: Session) -> tuple:
    b_client = api_client()
    a = build_world(client, db_session, "alice@example.com")
    b = build_world(b_client, db_session, "bob@example.com")
    return client, a, b_client, b


def test_cross_candidate_requests_are_404_and_change_nothing(
    worlds: tuple, db_session: Session
) -> None:
    a_client, a, b_client, b = worlds
    before = snapshot(db_session)
    count = 0
    for intruder, victim, own in ((b_client, a, b), (a_client, b, a)):
        for method, url, body in intruder_requests(victim, own):
            res = intruder.request(method, url, json=body)
            assert res.status_code == 404, (method, url, res.status_code, res.text)
            # Exactly what a missing resource says: nothing confirms that it exists.
            assert res.json()["detail"] in {"Candidate not found", "Resume not found",
                                            "Fact not found", "Interview session not found",
                                            "Question not found"}, (method, url)
            count += 1
    assert count == 70
    assert snapshot(db_session) == before


def test_a_foreign_id_answers_like_a_missing_one(worlds: tuple) -> None:
    a_client, a, _, b = worlds
    for template in ("/api/candidates/{}", "/api/resumes/{}", "/api/interview-sessions/{}"):
        kind = template.split("/")[2]
        foreign = {"candidates": b["candidate"], "resumes": b["resume"],
                   "interview-sessions": b["done"]}[kind]
        assert a_client.get(template.format(foreign)).json() == a_client.get(
            template.format(uuid.uuid4())).json()


def test_anonymous_requests_on_real_ids_are_401_and_change_nothing(
    worlds: tuple, db_session: Session
) -> None:
    _, a, _, b = worlds
    before = snapshot(db_session)
    anonymous = api_client()
    for method, url, body in intruder_requests(a, b):
        assert anonymous.request(method, url, json=body).status_code == 401, (method, url)
    assert snapshot(db_session) == before


@pytest.mark.parametrize("owner", ["a", "b"])
def test_each_candidate_still_reaches_their_own_resources(worlds: tuple, owner: str) -> None:
    a_client, a, b_client, b = worlds
    client, w = (a_client, a) if owner == "a" else (b_client, b)
    s = "/api/interview-sessions"
    expected = [
        ("GET", f"/api/candidates/{w['candidate']}", None, 200),
        ("GET", f"/api/candidates/{w['candidate']}/resumes", None, 200),
        ("GET", f"/api/candidates/{w['candidate']}/interview-sessions", None, 200),
        ("GET", f"/api/resumes/{w['resume']}", None, 200),
        ("GET", f"/api/resumes/{w['resume']}/facts", None, 200),
        ("GET", f"{s}/{w['done']}", None, 200),
        ("GET", f"{s}/{w['done']}/plan", None, 200),
        ("GET", f"{s}/{w['done']}/questions", None, 200),
        ("GET", f"{s}/{w['done']}/evaluations", None, 200),
        ("GET", f"{s}/{w['done']}/report", None, 200),
        ("GET", f"{s}/{w['done']}/ai-consent", None, 200),
        ("POST", f"{s}/{w['done']}/report", {}, 200),  # the same report again
        ("POST", f"{s}/{w['done']}/questions/{w['question']}/evaluation", {}, 200),  # stored
        ("POST", f"{s}/{w['done']}/retry", {}, 409),  # reached: blocked by the live session
        ("PATCH", f"/api/candidates/{w['candidate']}", {"name": "Renamed"}, 200),
        ("PATCH", f"/api/resumes/{w['resume']}/facts/{w['fact']}", {"status": "APPROVED"}, 200),
        ("POST", f"/api/resumes/{w['resume']}/ai-extraction", None, 503),  # no AI configured
        ("GET", f"/api/candidates/{w['candidate']}/manual-facts", None, 200),
        ("POST", f"/api/candidates/{w['candidate']}/manual-facts",
         {"category": "SKILL", "fact": "Rust"}, 201),
        ("PATCH", f"/api/manual-facts/{w['manual']}", {"fact": "Go 1.23"}, 200),
        ("DELETE", f"/api/manual-facts/{w['manual']}", None, 204),
        ("PUT", f"{s}/{w['live']}/ai-consent", {"granted": False}, 200),
        ("POST", f"{s}/{w['live']}/questions/next", {}, 409),  # not started yet
        ("POST", f"{s}/{w['live']}/answers",
         {"question_id": w["question"], "kind": "SKIP"}, 404),  # the question is of `done`
        ("POST", f"{s}/{w['live']}/actions", {"action": "CONFIRM_PROFILE"}, 200),
        ("POST", f"{s}/{w['live']}/plan", SETTINGS, 200),
        ("DELETE", f"{s}/{w['live']}", None, 204),
        ("DELETE", f"/api/resumes/{w['resume']}", None, 204),
        ("DELETE", f"{s}/{w['done']}", None, 204),
        ("DELETE", f"/api/candidates/{w['candidate']}", None, 204),
    ]
    for method, url, body, status in expected:
        res = client.request(method, url, json=body)
        assert res.status_code == status, (method, url, res.status_code, res.text)


def test_deleting_one_candidate_leaves_the_other_untouched(
    worlds: tuple, db_session: Session
) -> None:
    a_client, a, b_client, b = worlds
    before_b = {t: [r for r in rows if b["candidate"] in r or b["done"] in r or b["live"] in r]
                for t, rows in snapshot(db_session).items()}
    assert a_client.delete(f"/api/candidates/{a['candidate']}").status_code == 204
    after = snapshot(db_session)
    assert all(a["candidate"] not in r for rows in after.values() for r in rows)
    for t, rows in before_b.items():
        assert set(rows) <= set(after[t]), t
    assert me(b_client).json()["id"] == b["candidate"]


# ---------- real concurrency: separate, committed connections ----------


@pytest.fixture
def committed_email() -> Iterator[str]:
    email = f"{uuid.uuid4().hex}@example.com"
    yield email
    with SessionLocal() as db:
        db.execute(text("DELETE FROM candidates WHERE email = :e"), {"e": email})
        db.commit()


def run_parallel(*fns: Callable[[], object]) -> list:
    """Starts every call at once (a barrier) on its own thread; returns their results."""
    n = len(fns)
    barrier, results, errors = threading.Barrier(n), [], []

    def target(fn: Callable[[], object]) -> None:
        try:
            barrier.wait(10)
            results.append(fn())
        except Exception as exc:  # reported to the test thread
            errors.append(exc)

    threads = [threading.Thread(target=target, args=(fn,), daemon=True) for fn in fns]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not errors and len(results) == n
    return results


def test_simultaneous_registrations_with_one_email(committed_email: str) -> None:
    attempt = lambda: register(api_client(), email=committed_email).status_code  # noqa: E731
    results = run_parallel(attempt, attempt)
    assert sorted(results) == [201, 409]
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM candidates WHERE email = :e"),
                         {"e": committed_email}) == 1


@pytest.fixture
def committed_pair(committed_email: str) -> Iterator[tuple[str, str]]:
    other = f"{uuid.uuid4().hex}@example.com"
    stored = security.hash_password(PASSWORD)
    with SessionLocal() as db:
        db.add_all([Candidate(email=committed_email, name="Target", password_hash=stored),
                    Candidate(email=other, name="Bystander", password_hash=stored)])
        db.commit()
    yield committed_email, other
    with SessionLocal() as db:
        db.execute(text("DELETE FROM candidates WHERE email = :e"), {"e": other})
        db.commit()


def test_parallel_failed_logins_cannot_pass_the_threshold(committed_pair: tuple) -> None:
    target, bystander = committed_pair
    attempt = lambda: login(api_client(), email=target,  # noqa: E731
                            password="wrong password").status_code
    results = run_parallel(*[attempt] * 8)
    # Each attempt waits for the row lock: exactly five are counted, the rest meet the lock.
    assert sorted(results) == [401] * 5 + [429] * 3
    with SessionLocal() as db:
        row = db.execute(text("SELECT failed_logins, locked_until FROM candidates "
                              "WHERE email = :e"), {"e": target}).one()
        assert row.failed_logins == 0 and row.locked_until > datetime.now(UTC)
        assert tuple(db.execute(text("SELECT failed_logins, locked_until FROM candidates "
                                     "WHERE email = :e"), {"e": bystander}).one()) == (0, None)
    assert login(api_client(), email=target).status_code == 429
    assert login(api_client(), email=bystander).status_code == 200  # not locked by association


def test_logout_racing_requests_is_all_or_nothing(committed_pair: tuple) -> None:
    target, _ = committed_pair
    browser = api_client()
    assert login(browser, email=target).status_code == 200
    token = token_of(browser)

    def read() -> int:
        return me(api_client(token)).status_code

    def logout() -> int:
        return api_client(token).post("/api/auth/logout").status_code

    results = run_parallel(logout, *[read] * 8)
    # Every request is either fully signed in or fully refused; never a 500.
    assert results.count(204) == 1 and set(results) <= {200, 204, 401}
    assert me(api_client(token)).status_code == 401
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM auth_sessions WHERE token_hash = :h"),
                         {"h": security.token_hash(token)}) == 0

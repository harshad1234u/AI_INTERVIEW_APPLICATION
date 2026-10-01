"""Session-level AI consent (D2, D2b, D2c, Q5): API, history, planner gating, mid-call withdrawal.

The interviewer's side of consent is covered in test_interview_turn_api.py.
"""

import logging
import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.providers import get_model_gateway
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import InterviewConsentEvent, ProviderCall
from app.services.interview_state_machine import SessionEvent as E, apply_event
from tests.fakes import FakeProvider, make_gateway
from tests.test_interview_plan_api import (  # noqa: F401  (fixtures)
    EMAIL,
    NAME,
    SETTINGS,
    VALID,
    GatedProvider,
    candidate,
    committed_planning_session,
    consented,
    facts,
    plan,
    session_row,
    sid,
    use_gateway,
)
from tests.test_interview_sessions import PLAN


def consent(client: TestClient, session_id: object, granted: object):
    return client.put(f"/api/interview-sessions/{session_id}/ai-consent", json={"granted": granted})


def history(client: TestClient, session_id: object) -> dict:
    res = client.get(f"/api/interview-sessions/{session_id}/ai-consent")
    assert res.status_code == 200
    return res.json()


def test_consent_is_off_by_default_and_planning_then_calls_no_model(
    client: TestClient, sid: str, use_gateway
) -> None:  # K1
    assert history(client, sid) == {"session_id": sid, "granted": False, "history": []}
    provider = FakeProvider("groq", VALID)
    use_gateway(make_gateway(provider))
    body = plan(client, sid).json()
    assert (body["plan"]["source"], body["plan"]["rules_reason"], body["model_calls"]) == (
        "RULES", "NOT_REQUESTED", [])
    assert provider.calls == []


def test_granting_lets_the_planner_use_ai(client: TestClient, sid: str, use_gateway) -> None:  # K2
    provider = FakeProvider("groq", VALID)
    use_gateway(make_gateway(provider))
    res = consent(client, sid, True)
    assert res.status_code == 200
    assert (res.json()["session_id"], res.json()["granted"]) == (sid, True)
    assert res.json()["changed_at"] is not None
    assert plan(client, sid).json()["plan"]["source"] == "AI"
    assert len(provider.calls) == 1


def test_withdrawing_before_planning_means_no_call(
    client: TestClient, sid: str, use_gateway
) -> None:  # K3
    provider = FakeProvider("groq", VALID)
    use_gateway(make_gateway(provider))
    consent(client, sid, True)
    consent(client, sid, False)
    assert plan(client, sid).json()["plan"]["rules_reason"] == "NOT_REQUESTED"
    assert provider.calls == []


def test_history_records_each_change_once_with_its_time(
    client: TestClient, sid: str, db_session: Session
) -> None:  # K5, D2c
    for granted in (True, True, False, False, True):  # repeats are no-ops
        assert consent(client, sid, granted).status_code == 200
    body = history(client, sid)
    assert body["granted"] is True
    assert [h["granted"] for h in body["history"]] == [True, False, True]
    times = [h["changed_at"] for h in body["history"]]
    assert times == sorted(times) and len(set(times)) == 3
    assert set(body["history"][0]) == {"granted", "changed_at"}  # nothing else is kept
    # A repeat reports the time of the change that set the current value.
    assert consent(client, sid, True).json()["changed_at"] == times[-1]


def test_consent_can_be_given_before_planning_and_changed_in_any_state(
    client: TestClient, candidate: str, db_session: Session
) -> None:
    session_id = client.post("/api/interview-sessions", json={"candidate_id": candidate}).json()["id"]
    assert consent(client, session_id, True).status_code == 200  # PROFILE_REVIEW
    for event in (E.CONFIRM_PROFILE, E.PLAN_READY, E.START_INTERVIEW, E.QUESTION_ASKED,
                  E.END_INTERVIEW):
        apply_event(db_session, uuid.UUID(session_id), event,
                    plan=PLAN if event == E.PLAN_READY else None)
        db_session.commit()
        assert consent(client, session_id, False).status_code == 200
        assert consent(client, session_id, True).status_code == 200


def test_after_completion_consent_can_only_be_withdrawn(
    client: TestClient, sid: str, db_session: Session
) -> None:  # K6
    consent(client, sid, True)
    for event in (E.PLAN_READY, E.START_INTERVIEW, E.QUESTION_ASKED, E.END_INTERVIEW,
                  E.REPORT_READY):
        apply_event(db_session, uuid.UUID(sid), event, plan=PLAN if event == E.PLAN_READY else None)
        db_session.commit()
    assert consent(client, sid, False).status_code == 200
    res = consent(client, sid, True)
    assert (res.status_code, res.json()) == (409, {
        "detail": "This interview session is completed: AI consent can no longer be granted."})
    assert [h["granted"] for h in history(client, sid)["history"]] == [True, False]


@pytest.mark.parametrize("body", [{}, {"granted": "yes"}, {"granted": 1}, {"granted": None},
                                  {"granted": True, "status": "READY"}])
def test_invalid_consent_bodies_are_422(client: TestClient, sid: str, body: dict) -> None:
    res = client.put(f"/api/interview-sessions/{sid}/ai-consent", json=body)
    assert res.status_code == 422
    assert history(client, sid)["history"] == []


def test_unknown_session_is_404(client: TestClient) -> None:
    missing = uuid.uuid4()
    assert consent(client, missing, True).status_code == 404
    assert client.get(f"/api/interview-sessions/{missing}/ai-consent").status_code == 404
    assert consent(client, "not-a-uuid", True).status_code == 422


def test_consent_history_goes_with_the_session_and_the_candidate(
    client: TestClient, sid: str, candidate: str, db_session: Session
) -> None:
    consent(client, sid, True)
    assert client.delete(f"/api/candidates/{candidate}").status_code == 204
    assert db_session.scalar(text("SELECT count(*) FROM interview_consent_events")) == 0


def test_consent_logs_carry_ids_and_values_only(
    client: TestClient, sid: str, caplog: pytest.LogCaptureFixture
) -> None:  # K7
    caplog.set_level(logging.DEBUG)
    consent(client, sid, True)
    consent(client, sid, False)
    assert f"Interview session {sid}: AI consent granted" in caplog.text
    assert f"Interview session {sid}: AI consent withdrawn" in caplog.text
    for private in (NAME, EMAIL, "TrustLens", "React"):
        assert private not in caplog.text


def test_withdrawal_during_a_planner_call_discards_the_ai_plan(
    committed_planning_session: uuid.UUID,
) -> None:  # K4, N11(b)
    sid = committed_planning_session
    provider = GatedProvider({"topics": [
        {"competency": "project_understanding", "topic": "TrustLens architecture",
         "fact_refs": ["F1"], "question_templates": ["Explain the architecture of TrustLens."],
         "expected_concepts": []}]})
    app.dependency_overrides[get_model_gateway] = lambda: make_gateway(provider, timeout=30)
    consented(TestClient(app), sid)
    out: dict = {}

    def request() -> None:
        out["res"] = TestClient(app).post(f"/api/interview-sessions/{sid}/plan",
                                          json={**SETTINGS, "mode": "PROJECT_DEEP_DIVE"})

    thread = threading.Thread(target=request, daemon=True)
    try:
        thread.start()
        assert provider.arrived.acquire(timeout=10)  # the model is running
        assert engine.pool.checkedout() == 0  # no connection held...
        with engine.begin() as conn:  # ...and no row lock
            conn.execute(text("SELECT id FROM interview_sessions WHERE id = :i FOR UPDATE NOWAIT"),
                         {"i": sid})
        assert consent(TestClient(app), sid, False).status_code == 200
        provider.release.set()
        thread.join(30)
    finally:
        provider.release.set()
        app.dependency_overrides.pop(get_model_gateway, None)
    res = out["res"]
    assert res.status_code == 200
    stored = res.json()["plan"]
    assert (stored["source"], stored["rules_reason"]) == ("RULES", "CONSENT_WITHDRAWN")
    assert len(res.json()["model_calls"]) == 1
    with SessionLocal() as db:
        status, saved, call_id = session_row(db, sid)
        assert (status, saved, call_id) == ("READY", stored, None)  # the AI output is not kept
        assert db.scalar(select(ProviderCall.capability).where(
            ProviderCall.model == "gated-model")) == "INTERVIEW_PLANNING"  # the call is recorded
        assert list(db.scalars(select(InterviewConsentEvent.granted).where(
            InterviewConsentEvent.session_id == sid).order_by(InterviewConsentEvent.id))) == [
            True, False]

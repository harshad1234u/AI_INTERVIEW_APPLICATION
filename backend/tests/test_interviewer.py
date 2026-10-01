"""Interviewer (Phase 7): state machine bookkeeping, then the pure decision and wording rules."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.interview_session import FinishReason
from app.services.interview_state_machine import InvalidTransition, SessionEvent as E, apply_event
from tests.test_interview_sessions import PLAN, new_candidate

# ---------- state machine: clock and finish reasons (S1, T1, F1, F2) ----------


@pytest.fixture
def ready(client: TestClient, db_session: Session) -> uuid.UUID:
    cid = new_candidate(client)
    sid = client.post("/api/interview-sessions", json={"candidate_id": cid}).json()["id"]
    client.post(f"/api/interview-sessions/{sid}/actions", json={"action": "CONFIRM_PROFILE"})
    apply_event(db_session, uuid.UUID(sid), E.PLAN_READY, plan=PLAN)
    db_session.commit()
    return uuid.UUID(sid)


def clock(db: Session, sid: uuid.UUID) -> tuple:
    return tuple(db.execute(text(
        "SELECT status, active_seconds, active_since IS NOT NULL, finish_reason "
        "FROM interview_sessions WHERE id = :i"), {"i": sid}).one())


def run_for(db: Session, sid: uuid.UUID, seconds: int) -> None:
    """Pretend the clock has been running for `seconds` more (database time can't be pinned)."""
    db.execute(text("UPDATE interview_sessions SET active_since = active_since - "
                    "make_interval(secs => :s) WHERE id = :i"), {"s": seconds, "i": sid})


def step(db: Session, sid: uuid.UUID, event: E, **kwargs) -> None:
    apply_event(db, sid, event, **kwargs)
    db.commit()


def test_clock_runs_only_between_start_or_resume_and_pause_or_finish(
    db_session: Session, ready: uuid.UUID
) -> None:
    assert clock(db_session, ready) == ("READY", 0, False, None)
    step(db_session, ready, E.START_INTERVIEW)
    assert clock(db_session, ready)[1:3] == (0, True)
    step(db_session, ready, E.QUESTION_ASKED)
    run_for(db_session, ready, 100)
    step(db_session, ready, E.PAUSE)
    status, seconds, running, _ = clock(db_session, ready)
    assert (status, running) == ("PAUSED", False) and 100 <= seconds < 101
    # A long pause adds nothing (T6): the clock is stopped, not merely unobserved.
    db_session.execute(text("SELECT pg_sleep(0.05)"))
    step(db_session, ready, E.RESUME)
    assert clock(db_session, ready)[1] == seconds
    run_for(db_session, ready, 20)
    step(db_session, ready, E.END_INTERVIEW)
    status, final, running, reason = clock(db_session, ready)
    assert (status, running, reason) == ("REPORT_GENERATION", False, "CANDIDATE_ENDED")
    assert 120 <= final < 121  # frozen at the finish


def test_no_request_does_not_stop_the_clock(db_session: Session, ready: uuid.UUID) -> None:
    """Closing the tab sends nothing, so nothing pauses (D4c)."""
    step(db_session, ready, E.START_INTERVIEW)
    run_for(db_session, ready, 600)
    elapsed = db_session.scalar(text(
        "SELECT active_seconds + extract(epoch FROM clock_timestamp() - active_since) "
        "FROM interview_sessions WHERE id = :i"), {"i": ready})
    assert 600 <= elapsed < 601


@pytest.mark.parametrize(("events", "finish", "reason"), [
    ((E.START_INTERVIEW, E.TIME_EXPIRED), None, "TIME_LIMIT"),
    ((E.START_INTERVIEW, E.QUESTION_ASKED, E.TIME_EXPIRED), None, "TIME_LIMIT"),
    ((E.START_INTERVIEW, E.QUESTION_ASKED, E.END_INTERVIEW), None, "CANDIDATE_ENDED"),
    ((E.START_INTERVIEW, E.QUESTION_ASKED, E.PAUSE, E.END_INTERVIEW), None, "CANDIDATE_ENDED"),
    ((E.START_INTERVIEW, E.QUESTION_ASKED, E.ANSWER_SUBMITTED, E.ANSWER_PROCESSED,
      E.ANSWER_EVALUATED, E.FINISH), FinishReason.PLAN_COMPLETED, "PLAN_COMPLETED"),
    ((E.START_INTERVIEW, E.QUESTION_ASKED, E.ANSWER_SUBMITTED, E.ANSWER_PROCESSED,
      E.ANSWER_EVALUATED, E.FINISH), FinishReason.TIME_LIMIT, "TIME_LIMIT"),
])
def test_each_way_to_finish_sets_its_reason(
    db_session: Session, ready: uuid.UUID, events: tuple, finish: FinishReason | None, reason: str
) -> None:  # F1
    for event in events:
        step(db_session, ready, event, finish_reason=finish if event == E.FINISH else None)
    assert clock(db_session, ready)[::3] == ("REPORT_GENERATION", reason)
    step(db_session, ready, E.REPORT_READY)
    assert clock(db_session, ready)[::3] == ("COMPLETED", reason)  # kept for Phase 9


@pytest.mark.parametrize(("event", "reason"), [
    (E.FINISH, None), (E.FINISH, FinishReason.CANDIDATE_ENDED), (E.FINISH, "MODEL_SAID_SO"),
    (E.END_INTERVIEW, FinishReason.TIME_LIMIT), (E.TIME_EXPIRED, FinishReason.PLAN_COMPLETED),
    (E.PAUSE, FinishReason.TIME_LIMIT),
])
def test_finish_reason_only_with_finish_and_only_from_code(
    db_session: Session, ready: uuid.UUID, event: E, reason: object
) -> None:  # F2
    with pytest.raises(ValueError, match="FINISH needs"):
        apply_event(db_session, ready, event, finish_reason=reason)
    assert clock(db_session, ready) == ("READY", 0, False, None)


def test_time_expired_has_exactly_two_edges(db_session: Session, ready: uuid.UUID) -> None:
    with pytest.raises(InvalidTransition):  # READY: not started, so nothing to expire
        apply_event(db_session, ready, E.TIME_EXPIRED)
    step(db_session, ready, E.START_INTERVIEW)
    step(db_session, ready, E.QUESTION_ASKED)
    step(db_session, ready, E.PAUSE)
    with pytest.raises(InvalidTransition):  # PAUSED: the clock is stopped
        apply_event(db_session, ready, E.TIME_EXPIRED)

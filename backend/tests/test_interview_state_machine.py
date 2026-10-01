"""The transition table itself: pure, no database, no HTTP."""

import itertools

import pytest

from app.models.interview_session import InterviewStatus as S
from app.services.interview_state_machine import (
    TRANSITIONS,
    ClientAction,
    InvalidTransition,
    SessionEvent as E,
    next_status,
)

# Written out independently of the implementation: PRD §13 main path, §61 pause/resume,
# §59 "finishes early". A change to TRANSITIONS must be made here too, on purpose.
PRD_EDGES = [
    (S.CREATED, E.PROFILE_PROCESSING_STARTED, S.PROFILE_PROCESSING),
    (S.PROFILE_PROCESSING, E.PROFILE_READY, S.PROFILE_REVIEW),
    (S.PROFILE_REVIEW, E.CONFIRM_PROFILE, S.INTERVIEW_PLANNING),
    (S.INTERVIEW_PLANNING, E.PLAN_READY, S.READY),
    (S.READY, E.START_INTERVIEW, S.ASKING),
    (S.ASKING, E.QUESTION_ASKED, S.WAITING_FOR_ANSWER),
    (S.WAITING_FOR_ANSWER, E.ANSWER_SUBMITTED, S.ANSWER_PROCESSING),
    (S.ANSWER_PROCESSING, E.ANSWER_PROCESSED, S.ANSWER_EVALUATION),
    (S.ANSWER_EVALUATION, E.ANSWER_EVALUATED, S.NEXT_DECISION),
    (S.NEXT_DECISION, E.FOLLOW_UP, S.ASKING),
    (S.NEXT_DECISION, E.NEXT_TOPIC, S.ASKING),
    (S.NEXT_DECISION, E.REPHRASE, S.ASKING),
    (S.NEXT_DECISION, E.FINISH, S.REPORT_GENERATION),
    (S.REPORT_GENERATION, E.REPORT_READY, S.COMPLETED),
    (S.WAITING_FOR_ANSWER, E.PAUSE, S.PAUSED),
    (S.PAUSED, E.RESUME, S.WAITING_FOR_ANSWER),
    (S.WAITING_FOR_ANSWER, E.END_INTERVIEW, S.REPORT_GENERATION),
    (S.PAUSED, E.END_INTERVIEW, S.REPORT_GENERATION),
    # Phase 7 (Q1): the time limit, raised by the application only
    (S.ASKING, E.TIME_EXPIRED, S.REPORT_GENERATION),
    (S.WAITING_FOR_ANSWER, E.TIME_EXPIRED, S.REPORT_GENERATION),
]
ALLOWED = {(frm, ev) for frm, ev, _ in PRD_EDGES}
FORBIDDEN = [pair for pair in itertools.product(S, E) if pair not in ALLOWED]


def test_table_is_exactly_the_prd_lifecycle() -> None:
    assert TRANSITIONS == {(frm, ev): to for frm, ev, to in PRD_EDGES}


@pytest.mark.parametrize(("frm", "event", "to"), PRD_EDGES, ids=lambda x: str(x))
def test_permitted_transition(frm: S, event: E, to: S) -> None:
    assert next_status(frm, event) == to
    assert next_status(frm.value, event.value) == to  # plain strings from the DB/API work too


@pytest.mark.parametrize(("frm", "event"), FORBIDDEN, ids=lambda x: str(x))
def test_forbidden_transition(frm: S, event: E) -> None:
    with pytest.raises(InvalidTransition) as exc:
        next_status(frm, event)
    assert str(exc.value) == f"Cannot {event} an interview session in {frm}."


def test_forbidden_list_is_the_full_complement() -> None:
    assert len(FORBIDDEN) == len(S) * len(E) - len(PRD_EDGES) == 13 * 18 - 20


def test_completed_is_terminal() -> None:
    assert not [ev for (frm, ev) in TRANSITIONS if frm == S.COMPLETED]


def test_every_state_is_reachable_and_can_still_finish() -> None:
    graph: dict[S, set[S]] = {}
    for (frm, _), to in TRANSITIONS.items():
        graph.setdefault(frm, set()).add(to)

    def reachable(start: S) -> set[S]:
        seen, todo = {start}, [start]
        while todo:
            for nxt in graph.get(todo.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    assert reachable(S.CREATED) == set(S)  # no orphan state
    assert all(S.COMPLETED in reachable(s) for s in S)  # no dead end short of COMPLETED


@pytest.mark.parametrize(
    ("status", "event"),
    [(S.WAITING_FOR_ANSWER, "pause"), (S.WAITING_FOR_ANSWER, "SKIP"), (S.READY, ""),
     (S.READY, None), (S.READY, 42), (S.READY, "START_INTERVIEW "),
     ("TRUSTED", E.PAUSE), ("", E.PAUSE), (None, E.CONFIRM_PROFILE), ("profile_review", E.CONFIRM_PROFILE)],
)
def test_unknown_or_malformed_events_and_statuses_are_rejected(status: object, event: object) -> None:
    with pytest.raises(InvalidTransition):
        next_status(status, event)


def test_client_actions_are_exactly_the_five_and_no_system_event() -> None:
    assert {a.value for a in ClientAction} == {
        "CONFIRM_PROFILE", "START_INTERVIEW", "PAUSE", "RESUME", "END_INTERVIEW"
    }
    assert {a.value for a in ClientAction} <= {e.value for e in E}
    system = {e for e in E if e.value not in {a.value for a in ClientAction}}
    assert {e.value for e in system} == {
        "PROFILE_PROCESSING_STARTED", "PROFILE_READY", "PLAN_READY", "QUESTION_ASKED",
        "ANSWER_SUBMITTED", "ANSWER_PROCESSED", "ANSWER_EVALUATED", "FOLLOW_UP", "NEXT_TOPIC",
        "REPHRASE", "FINISH", "REPORT_READY", "TIME_EXPIRED",
    }

"""Optional camera expression observations: counts only, cautious wording, never in a score."""

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.expression import ExpressionStatus, QuestionExpressionObservation
from app.services.expressions import DISCLAIMER, NOT_ENABLED, UNAVAILABLE, describe
from tests.auth_helpers import api_client, make_candidate
from tests.test_evaluation_api import finished  # noqa: F401  (fixture)
from tests.test_interview_plan_api import candidate, facts, sid  # noqa: F401  (fixtures)
from tests.test_interview_turn_api import act, ans, first_question, started  # noqa: F401

FORBIDDEN = re.compile(r"nervous|anxious|anxiety|confiden|lying|dishonest|honest\b|unsuitable|"
                       r"\bfelt\b|\bfeel|emotion(?!, personality)|%|\d+\s*percent", re.IGNORECASE)


def row(status=ExpressionStatus.ANALYZED, **counts) -> QuestionExpressionObservation:
    values = dict.fromkeys(("neutral", "happy", "sad", "angry", "fearful", "disgusted",
                            "surprised", "no_face", "multiple_faces"), 0)
    return QuestionExpressionObservation(question_id=uuid.uuid4(), status=status,
                                         **{**values, **counts})


@pytest.mark.parametrize("counts, text", [
    ({"neutral": 10}, "Mostly neutral expression."),
    ({"neutral": 7, "happy": 3}, "Mostly neutral expression, with occasional smiling expression."),
    ({"neutral": 4, "happy": 4, "surprised": 2}, "Mixed: neutral and smiling expressions."),
    ({"angry": 4, "disgusted": 4, "neutral": 2}, "Mostly frowning expression, with occasional "
                                                  "neutral expression."),  # look-alikes merged
    ({"neutral": 2}, "Insufficient visual data (the face was rarely visible)."),
    ({"neutral": 5, "no_face": 9}, "Mostly neutral expression; the face was often not visible."),
    ({"happy": 6, "multiple_faces": 1}, "Mostly smiling expression."),
])
def test_wording_is_cautious_and_has_no_numbers(counts: dict, text: str) -> None:
    assert describe(row(**counts)) == text
    assert not FORBIDDEN.search(text)


def test_unavailable_and_the_disclaimer() -> None:
    assert describe(row(ExpressionStatus.UNAVAILABLE)) == "Unavailable for this question."
    assert "not measurements of emotion, personality, confidence, honesty or suitability" \
        in DISCLAIMER and "never used in any score" in DISCLAIMER


def put(client: TestClient, sid: str, qid: str, **body):
    return client.put(f"/api/interview-sessions/{sid}/questions/{qid}/expressions",
                      json={"status": "ANALYZED", **body})


def evaluate_all(client: TestClient, sid: str) -> None:
    """No AI consent: deterministic observations, so the report can be built."""
    for q in client.get(f"/api/interview-sessions/{sid}/questions").json()["questions"]:
        if q["answer"] and q["answer"]["kind"] == "ANSWER":
            assert client.post(f"/api/interview-sessions/{sid}/questions/{q['id']}/evaluation",
                               json={}).status_code == 200


def report(client: TestClient, sid: str) -> dict:
    evaluate_all(client, sid)
    res = client.post(f"/api/interview-sessions/{sid}/report", json={})
    assert res.status_code == 200, res.text
    return res.json()["report"]


def test_no_camera_means_not_enabled_and_nothing_else_changes(
    client: TestClient, started: str, finished: dict  # noqa: F811
) -> None:
    signals = report(client, started)["expression_signals"]
    assert signals == {"available": False, "note": NOT_ENABLED, "questions": []}


def test_observations_reach_the_report_and_never_any_score(
    client: TestClient, started: str, finished: dict, db_session: Session  # noqa: F811
) -> None:
    from app.models import InterviewSession
    from app.services.report import session_report
    tech, behavioral = finished["tech"]["id"], finished["behavioral"]["id"]
    assert put(client, started, tech, counts={"neutral": 8, "happy": 2}).status_code == 204
    assert put(client, started, behavioral, counts={"happy": 1}, no_face=6).status_code == 204
    full = report(client, started)
    # The same report without the observations differs only in that one section.
    db_session.execute(text("DELETE FROM question_expression_observations"))
    without = session_report(db_session, db_session.get(InterviewSession, uuid.UUID(started)))
    assert {k: v for k, v in without.model_dump(mode="json").items()
            if k != "expression_signals"} == {k: v for k, v in full.items()
                                               if k != "expression_signals"}
    signals = full["expression_signals"]
    assert (signals["available"], signals["note"]) == (True, DISCLAIMER)
    assert [(q["seq"], q["summary"]) for q in signals["questions"]] == [
        (finished["tech"]["seq"], "Mostly neutral expression, with occasional smiling expression."),
        (finished["behavioral"]["seq"], "Insufficient visual data (the face was rarely visible).")]
    # Completed now: the report no longer changes.
    res = put(client, started, tech, counts={"sad": 9})
    assert (res.status_code, res.json()["detail"]) == (
        409, "Expression observations can only be saved for an interview in progress.")


def test_a_replay_replaces_and_unavailable_stores_no_counts(
    client: TestClient, started: str, finished: dict, db_session: Session  # noqa: F811
) -> None:
    qid = finished["tech"]["id"]
    assert put(client, started, qid, counts={"neutral": 5}).status_code == 204
    assert put(client, started, qid, status="UNAVAILABLE", counts={"neutral": 5}).status_code == 204
    stored = db_session.execute(text(
        "SELECT status, neutral FROM question_expression_observations WHERE question_id = :q"),
        {"q": qid}).one()
    assert tuple(stored) == ("UNAVAILABLE", 0)
    assert report(client, started)["expression_signals"] == {
        "available": False, "note": UNAVAILABLE, "questions": []}


@pytest.mark.parametrize("body", [
    {"counts": {"lying": 1}}, {"counts": {"happy": -1}}, {"counts": {"happy": 10_001}},
    {"frame": "data:image/jpeg;base64,AAAA"}, {"status": "MAYBE"}, {"no_face": -2},
])
def test_only_counts_are_accepted(client: TestClient, started: str, finished: dict,  # noqa: F811
                                  body: dict) -> None:
    assert put(client, started, finished["tech"]["id"], **body).status_code == 422


def test_unanswered_unknown_and_foreign_questions(
    client: TestClient, started: str, finished: dict, db_session: Session  # noqa: F811
) -> None:
    assert put(client, started, finished["open"]["id"]).status_code == 409  # never answered
    assert put(client, started, str(uuid.uuid4())).status_code == 404
    other = api_client()
    make_candidate(other, db_session, "intruder@example.com", "Intruder")
    res = put(other, started, finished["tech"]["id"], counts={"happy": 9})
    assert (res.status_code, res.json()["detail"]) == (404, "Interview session not found")
    assert db_session.scalar(text("SELECT count(*) FROM question_expression_observations")) == 0


def test_deleting_the_interview_deletes_its_observations(
    client: TestClient, started: str, finished: dict, db_session: Session  # noqa: F811
) -> None:
    assert put(client, started, finished["tech"]["id"], counts={"neutral": 4}).status_code == 204
    assert client.delete(f"/api/interview-sessions/{started}").status_code == 204
    assert db_session.scalar(text("SELECT count(*) FROM question_expression_observations")) == 0


def test_nothing_that_decides_or_scores_reads_observations() -> None:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    for name in ("interviewer.py", "evaluator.py", "interview_planner.py", "retry.py",
                 "limits.py", "interview_state_machine.py"):
        source = (app_dir / "services" / name).read_text(encoding="utf-8")
        assert "expression" not in source.lower(), name
    for agent in (app_dir / "ai").glob("*.py"):
        assert "expression" not in agent.read_text(encoding="utf-8").lower(), agent.name

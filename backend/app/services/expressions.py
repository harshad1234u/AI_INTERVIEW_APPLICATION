"""Observed facial-expression signals: an optional, experimental observation (not a measurement).

The browser runs a small expression model on the candidate's own device and sends, per question,
only how many samples fell into each class. Here those counts are turned into cautious, plain
words for the report. Nothing here is read by the interviewer, the evaluator, the report's
criteria or any score, and no wording says what the candidate felt, intended or is.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewQuestion
from app.models.expression import EXPRESSIONS, ExpressionStatus, QuestionExpressionObservation
from app.models.interview_session import InterviewStatus
from app.schemas.report import ExpressionSignal, ExpressionSignals
from app.services.interviewer import QuestionNotFound, lock_session

# What the model's classes look like, never what someone feels. Classes that look alike on a
# face are merged so the wording does not pretend to more precision than the model has.
LOOKS = {
    "neutral": "neutral",
    "happy": "smiling",
    "surprised": "surprised-looking",
    "sad": "downcast-looking",
    "angry": "frowning",
    "disgusted": "frowning",
    "fearful": "tense-looking",
}
MIN_SAMPLES = 3  # fewer analysed samples than this says nothing
MOSTLY, OCCASIONAL = 0.6, 0.2

DISCLAIMER = (
    "These observations describe visible facial-expression patterns detected on your own device "
    "while you answered. They are experimental and approximate. They are not measurements of "
    "emotion, personality, confidence, honesty or suitability, and they are never used in any "
    "score, feedback or decision.")
NOT_ENABLED = "Not available: the camera was not enabled for this interview."
UNAVAILABLE = "Unavailable during this interview."
NOT_FINISHED = "Expression observations can only be saved for an interview in progress."
NOT_ANSWERED = "Expression observations can only be saved for a question that was answered."


class ObservationNotAllowed(Exception):
    """409. The message names the reason, never any content."""


def describe(row: QuestionExpressionObservation) -> str:
    """One cautious sentence for one question. Deterministic; no percentages."""
    if row.status == ExpressionStatus.UNAVAILABLE:
        return "Unavailable for this question."
    looks: dict[str, int] = {}
    for name in EXPRESSIONS:
        looks[LOOKS[name]] = looks.get(LOOKS[name], 0) + getattr(row, name)
    seen = sum(looks.values())
    if seen < MIN_SAMPLES:
        return "Insufficient visual data (the face was rarely visible)."
    ranked = sorted(looks.items(), key=lambda kv: (-kv[1], kv[0]))
    top, top_n = ranked[0]
    if top_n / seen >= MOSTLY:
        text = f"Mostly {top} expression"
        also = [name for name, n in ranked[1:] if n / seen >= OCCASIONAL]
        if also:
            text += f", with occasional {' and '.join(also)} expression"
    else:
        text = f"Mixed: {top} and {ranked[1][0]} expressions"
    misses = row.no_face + row.multiple_faces
    if misses > seen:
        text += "; the face was often not visible"
    return text + "."


def signals(history: list[InterviewQuestion],
            rows: dict[uuid.UUID, QuestionExpressionObservation]) -> ExpressionSignals:
    asked = [q for q in history if q.id in rows]
    if not asked:
        return ExpressionSignals(available=False, note=NOT_ENABLED, questions=[])
    if all(rows[q.id].status == ExpressionStatus.UNAVAILABLE for q in asked):
        return ExpressionSignals(available=False, note=UNAVAILABLE, questions=[])
    return ExpressionSignals(available=True, note=DISCLAIMER, questions=[
        ExpressionSignal(question_id=q.id, seq=q.seq, summary=describe(rows[q.id]))
        for q in asked])


def session_observations(db: Session, session_id: uuid.UUID
                         ) -> dict[uuid.UUID, QuestionExpressionObservation]:
    rows = db.scalars(
        select(QuestionExpressionObservation)
        .join(InterviewQuestion, InterviewQuestion.id == QuestionExpressionObservation.question_id)
        .where(InterviewQuestion.session_id == session_id))
    return {r.question_id: r for r in rows}


def save_observation(db: Session, session_id: uuid.UUID, question_id: uuid.UUID,
                     status: ExpressionStatus, counts: dict[str, int]) -> None:
    """Stores (or replaces) one answered question's counts, under the session row lock. Only
    while the interview is running or awaiting its report: a completed report never changes.
    The caller commits."""
    session = lock_session(db, session_id)
    if session.status == InterviewStatus.COMPLETED or session.plan is None \
            or session.status == InterviewStatus.READY:
        raise ObservationNotAllowed(NOT_FINISHED)
    question = db.get(InterviewQuestion, question_id)
    if question is None or question.session_id != session.id:
        raise QuestionNotFound(question_id)
    if question.answered_at is None:
        raise ObservationNotAllowed(NOT_ANSWERED)
    values = {name: counts.get(name, 0) if status == ExpressionStatus.ANALYZED else 0
              for name in (*EXPRESSIONS, "no_face", "multiple_faces")}
    row = db.get(QuestionExpressionObservation, question_id)
    if row is None:
        db.add(QuestionExpressionObservation(question_id=question_id, status=status, **values))
    else:
        row.status = status
        for name, value in values.items():
            setattr(row, name, value)
    db.flush()

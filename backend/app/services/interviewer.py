"""Interviewer (PRD §12-§17, §29-§33): consent, deadline, decisions, wording rules, persistence.

LLM proposes, orchestrator decides (PRD §57). Every action, topic, finish and finish reason is
chosen here by code; a model only proposes the wording of a FOLLOW_UP or REPHRASE that code has
already chosen (app/ai/interviewer_agent.py), and that wording is validated here before use.

Transaction contract (as in the planner): no connection or row lock is held while a model runs.
prepare_turn() locks, decides and either finishes the turn itself or commits and hands back what
the model needs; save_turn() locks again, re-checks everything that may have changed, and writes.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewConsentEvent, InterviewSession
from app.models.interview_session import InterviewStatus
from app.services.interview_state_machine import SessionNotFound

logger = logging.getLogger(__name__)
S = InterviewStatus


class ConsentNotAllowed(Exception):
    def __init__(self) -> None:
        super().__init__("This interview session is completed: AI consent can no longer be granted.")


def lock_session(db: Session, session_id: uuid.UUID) -> InterviewSession:
    """The session row, locked, as last committed (the same lock apply_event takes)."""
    session = db.scalar(
        select(InterviewSession)
        .where(InterviewSession.id == session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if session is None:
        raise SessionNotFound(session_id)
    return session


# ---------- consent (D2, D2b, D2c) ----------


def set_consent(db: Session, session_id: uuid.UUID, granted: bool) -> InterviewSession:
    """Grant or withdraw AI consent under the row lock. A change is recorded with its time; a
    repeat of the current value records nothing. Withdrawing is always allowed. The caller
    commits."""
    session = lock_session(db, session_id)
    if granted and session.status == S.COMPLETED:
        raise ConsentNotAllowed()
    if session.ai_consent != granted:
        session.ai_consent = granted
        db.add(InterviewConsentEvent(session_id=session.id, granted=granted))
        db.flush()
        # Ids and the new value only (D2c).
        logger.info("Interview session %s: AI consent %s", session.id,
                    "granted" if granted else "withdrawn")
    return session


def consent_history(db: Session, session_id: uuid.UUID) -> list[InterviewConsentEvent]:
    return list(db.scalars(
        select(InterviewConsentEvent)
        .where(InterviewConsentEvent.session_id == session_id)
        .order_by(InterviewConsentEvent.id)
    ))

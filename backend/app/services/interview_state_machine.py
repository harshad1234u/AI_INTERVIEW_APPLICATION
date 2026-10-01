"""Interview lifecycle: the one place that decides which state changes are allowed.

The API and (in later phases) the orchestrator change a session only through `create_session`
and `apply_event`; nothing else writes `InterviewSession.status`. An LLM can at most *propose* an
event such as FOLLOW_UP: it goes through the same table and checks as everything else.

Transaction contract: these functions flush but never commit. The caller commits on success and
rolls back on any exception, which also releases the row lock. Never hold that lock across an LLM
or other external call: transition and commit first, call out, then apply the next event, which is
re-checked against whatever state the session is in by then.
"""

import logging
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.interview_session import (
    ONE_ACTIVE_SESSION_INDEX,
    FinishReason,
    InterviewSession,
    InterviewStatus,
)
from app.models.resume import CandidateFact, FactStatus

logger = logging.getLogger(__name__)
S = InterviewStatus


class ClientAction(StrEnum):
    """The only events the HTTP API accepts."""

    CONFIRM_PROFILE = "CONFIRM_PROFILE"
    START_INTERVIEW = "START_INTERVIEW"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    END_INTERVIEW = "END_INTERVIEW"


class SessionEvent(StrEnum):
    # Client actions (same values as ClientAction)
    CONFIRM_PROFILE = "CONFIRM_PROFILE"
    START_INTERVIEW = "START_INTERVIEW"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    END_INTERVIEW = "END_INTERVIEW"
    # System events: raised by the application/orchestrator, never accepted over HTTP
    PROFILE_PROCESSING_STARTED = "PROFILE_PROCESSING_STARTED"
    PROFILE_READY = "PROFILE_READY"
    PLAN_READY = "PLAN_READY"  # Planner (Phase 6)
    QUESTION_ASKED = "QUESTION_ASKED"  # Interviewer (Phase 7)
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"  # Phase 7's answer endpoint, with the answer itself
    ANSWER_PROCESSED = "ANSWER_PROCESSED"
    ANSWER_EVALUATED = "ANSWER_EVALUATED"  # Evaluator (Phase 8)
    # The orchestrator's decision (PRD §29): actions, not stored states
    FOLLOW_UP = "FOLLOW_UP"
    NEXT_TOPIC = "NEXT_TOPIC"
    REPHRASE = "REPHRASE"
    FINISH = "FINISH"
    REPORT_READY = "REPORT_READY"  # Coach (Phase 9)
    # The time limit (Phase 7): raised by the application when it finds the deadline passed
    TIME_EXPIRED = "TIME_EXPIRED"


E = SessionEvent

# (current status, event) -> next status. Anything not listed is rejected. COMPLETED is terminal.
TRANSITIONS: dict[tuple[InterviewStatus, SessionEvent], InterviewStatus] = {
    # PRD §13 main path
    (S.CREATED, E.PROFILE_PROCESSING_STARTED): S.PROFILE_PROCESSING,
    (S.PROFILE_PROCESSING, E.PROFILE_READY): S.PROFILE_REVIEW,
    (S.PROFILE_REVIEW, E.CONFIRM_PROFILE): S.INTERVIEW_PLANNING,
    (S.INTERVIEW_PLANNING, E.PLAN_READY): S.READY,
    (S.READY, E.START_INTERVIEW): S.ASKING,
    (S.ASKING, E.QUESTION_ASKED): S.WAITING_FOR_ANSWER,
    (S.WAITING_FOR_ANSWER, E.ANSWER_SUBMITTED): S.ANSWER_PROCESSING,
    (S.ANSWER_PROCESSING, E.ANSWER_PROCESSED): S.ANSWER_EVALUATION,
    (S.ANSWER_EVALUATION, E.ANSWER_EVALUATED): S.NEXT_DECISION,
    (S.NEXT_DECISION, E.FOLLOW_UP): S.ASKING,
    (S.NEXT_DECISION, E.NEXT_TOPIC): S.ASKING,
    (S.NEXT_DECISION, E.REPHRASE): S.ASKING,
    (S.NEXT_DECISION, E.FINISH): S.REPORT_GENERATION,
    (S.REPORT_GENERATION, E.REPORT_READY): S.COMPLETED,
    # PRD §61 recovery: only while the candidate holds the turn and no system work is in flight,
    # so RESUME always knows where to return.
    (S.WAITING_FOR_ANSWER, E.PAUSE): S.PAUSED,
    (S.PAUSED, E.RESUME): S.WAITING_FOR_ANSWER,
    # PRD §59 "user finishes early": generate a partial report
    (S.WAITING_FOR_ANSWER, E.END_INTERVIEW): S.REPORT_GENERATION,
    (S.PAUSED, E.END_INTERVIEW): S.REPORT_GENERATION,
    # PRD §12 "interview timeout": the application ends the interview at the time limit. (From
    # NEXT_DECISION it uses FINISH with TIME_LIMIT; PAUSED stops the clock, so it cannot expire.)
    (S.ASKING, E.TIME_EXPIRED): S.REPORT_GENERATION,
    (S.WAITING_FOR_ANSWER, E.TIME_EXPIRED): S.REPORT_GENERATION,
}
# FINISH must say why; the other ways into REPORT_GENERATION imply it.
FINISH_REASONS = (FinishReason.PLAN_COMPLETED, FinishReason.TIME_LIMIT)
IMPLIED_FINISH_REASON = {E.END_INTERVIEW: FinishReason.CANDIDATE_ENDED,
                         E.TIME_EXPIRED: FinishReason.TIME_LIMIT}


class SessionNotFound(Exception):
    pass


class InvalidTransition(Exception):
    def __init__(self, status: object, event: object) -> None:
        super().__init__(f"Cannot {event} an interview session in {status}.")
        self.status, self.event = status, event


class ProfileNotReviewed(Exception):
    def __init__(self, pending: int) -> None:
        super().__init__(
            f"Review your extracted profile facts before confirming: {pending} still pending."
        )
        self.pending = pending


class ActiveSessionExists(Exception):
    def __init__(self, session_id: uuid.UUID | None) -> None:
        super().__init__("active session exists")
        self.session_id = session_id  # None if it finished or was deleted in the meantime


def next_status(status: object, event: object) -> InterviewStatus:
    """Pure lookup in the transition table. Unknown statuses and events are rejected too."""
    try:
        return TRANSITIONS[(InterviewStatus(status), SessionEvent(event))]
    except (KeyError, ValueError):
        raise InvalidTransition(status, event) from None


def create_session(db: Session, candidate_id: uuid.UUID) -> InterviewSession:
    """New session for an existing candidate, persisted in PROFILE_REVIEW.

    Profile processing is candidate-level and synchronous today, so the session has no work of
    its own in CREATED or PROFILE_PROCESSING: both transitions are applied before the insert.
    """
    status = S.CREATED
    for event in (E.PROFILE_PROCESSING_STARTED, E.PROFILE_READY):
        status = next_status(status, event)
    session = InterviewSession(candidate_id=candidate_id, status=status)
    try:
        with db.begin_nested():  # a duplicate rolls back to here; the transaction stays usable
            db.add(session)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint != ONE_ACTIVE_SESSION_INDEX:
            raise
        # Scoped to this candidate, so only their own session id can ever be reported.
        existing = db.scalar(
            select(InterviewSession.id).where(
                InterviewSession.candidate_id == candidate_id,
                InterviewSession.status != S.COMPLETED,
            )
        )
        raise ActiveSessionExists(existing) from None
    logger.info("Interview session %s created: %s", session.id, session.status)
    return session


def apply_event(
    db: Session,
    session_id: uuid.UUID,
    event: SessionEvent,
    *,
    plan: dict[str, Any] | None = None,
    finish_reason: FinishReason | None = None,
) -> InterviewSession:
    """Lock the session row, check the event against its latest committed state, apply it.

    PLAN_READY must carry the validated plan, written in the same flush as READY (the database
    rejects one without the other); no other event may carry one. Likewise FINISH must carry its
    reason (PLAN_COMPLETED or TIME_LIMIT), and only FINISH takes one.

    Also keeps the active-time clock, in database time: START_INTERVIEW and RESUME start it; PAUSE
    and every move into REPORT_GENERATION add the running time to active_seconds and stop it.
    """
    if (event == E.PLAN_READY) != (plan is not None):
        raise ValueError("PLAN_READY needs the validated plan, and only PLAN_READY takes one")
    if (event == E.FINISH) != (finish_reason is not None) or (
            finish_reason is not None and finish_reason not in FINISH_REASONS):
        raise ValueError("FINISH needs PLAN_COMPLETED or TIME_LIMIT, and only FINISH takes a reason")
    session = db.scalar(
        select(InterviewSession)
        .where(InterviewSession.id == session_id)
        .with_for_update()
        # The row may already be in this Session from an earlier read: replace it with the
        # version just locked, so a transition that was valid before waiting is re-checked.
        .execution_options(populate_existing=True)
    )
    if session is None:
        raise SessionNotFound(session_id)
    old = session.status
    new = next_status(old, event)
    if event == E.CONFIRM_PROFILE:
        _require_reviewed_profile(db, session.candidate_id)
    session.status = new
    if plan is not None:
        session.plan = plan
    if event in (E.START_INTERVIEW, E.RESUME):
        session.active_since = func.clock_timestamp()
    if event == E.PAUSE or new == S.REPORT_GENERATION:
        # One UPDATE: the right-hand side sees the old active_since. NULL (already stopped, e.g.
        # END_INTERVIEW while PAUSED) adds nothing.
        session.active_seconds = InterviewSession.active_seconds + func.coalesce(
            func.extract("epoch", func.clock_timestamp() - InterviewSession.active_since), 0)
        session.active_since = None
    if new == S.REPORT_GENERATION:
        session.finish_reason = finish_reason or IMPLIED_FINISH_REASON[event]
    # clock_timestamp, not now(): now() is the transaction start, which can be earlier than the
    # commit of a transition this one waited for.
    session.updated_at = func.clock_timestamp()
    db.flush()
    logger.info("Interview session %s: %s -> %s on %s%s", session.id, old, new, event,
                f" ({session.finish_reason})" if new == S.REPORT_GENERATION else "")
    return session


def _require_reviewed_profile(db: Session, candidate_id: uuid.UUID) -> None:
    # A fresh query after the lock, so it sees every fact review committed so far. Facts can only
    # leave PENDING_REVIEW, or arrive as new pending facts; a fact committed after this check is
    # simply one that arrived after the confirmation. Later phases must use approved facts only.
    pending = db.scalar(
        select(func.count())
        .select_from(CandidateFact)
        .where(CandidateFact.candidate_id == candidate_id,
               CandidateFact.status == FactStatus.PENDING_REVIEW)
    )
    if pending:
        raise ProfileNotReviewed(pending)

"""Retry practice sessions (Phase 10, docs/phase-10-retry-plan.md).

A completed interview's report names its topics to practise. A retry is a new, normal session
whose plan is exactly those topics, copied word for word from the stored plan snapshot. Nothing
is generated and no model is called. The report is the only definition of "to practise", and the
interviewer's own D8 check decides which topics' facts are still valid.

Transaction contract (as elsewhere): create_retry() locks the source row and does everything in
the caller's transaction. The caller commits; any exception leaves nothing.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models import InterviewSession
from app.models.interview_session import InterviewStatus
from app.schemas.interview_plan import InterviewPlan
from app.services.interview_state_machine import SessionEvent, apply_event, create_session
from app.services.interviewer import lock_session, stored_plan, valid_positions
from app.services.report import session_report

logger = logging.getLogger(__name__)

NOT_COMPLETED = "Retry is available after the report has been generated."
NOTHING_TO_RETRY = "There are no topics to retry."
FACTS_CHANGED = "No topic can be retried: the profile details they relied on have changed."


class RetryNotAllowed(Exception):
    """409. The message names the reason; never any content."""


def retry_plan(plan: InterviewPlan, positions: list[int]) -> InterviewPlan:
    """The plan of a retry: the topics at these positions, unchanged except for their new
    positions. Settings, provenance (source, rules_reason) and omitted groups are kept; the
    competencies are those of the kept topics, as in build_plan. Pure."""
    topics = [plan.topics[p - 1].model_copy(update={"position": i})
              for i, p in enumerate(positions, 1)]
    return InterviewPlan.model_validate({
        **plan.model_dump(mode="json"),
        "competencies": list(dict.fromkeys(t.competency for t in topics)),
        "topics": [t.model_dump(mode="json") for t in topics],
    })


def create_retry(db: Session, source_id: uuid.UUID) -> tuple[InterviewSession, InterviewPlan]:
    """A READY session for the source's candidate with every topic to practise whose cited facts
    are still approved and unchanged. The source is only read (under its row lock)."""
    source = lock_session(db, source_id)
    if source.status != InterviewStatus.COMPLETED:
        raise RetryNotAllowed(NOT_COMPLETED)
    wanted = [t.topic_position for t in session_report(db, source).topics_to_practise]
    if not wanted:
        raise RetryNotAllowed(NOTHING_TO_RETRY)
    plan = stored_plan(source)
    valid = valid_positions(db, source.candidate_id, plan)
    kept = [p for p in wanted if p in valid]
    if not kept:
        raise RetryNotAllowed(FACTS_CHANGED)
    new_plan = retry_plan(plan, kept)
    # The normal lifecycle: the one-active-session index, the pending-facts check and PLAN_READY.
    # The new session's AI consent is its own column default (false); nothing is copied.
    session = create_session(db, source.candidate_id)
    session.retry_of_id = source.id
    apply_event(db, session.id, SessionEvent.CONFIRM_PROFILE)
    session = apply_event(db, session.id, SessionEvent.PLAN_READY,
                          plan=new_plan.model_dump(mode="json"))
    logger.info("Interview session %s: retry of %s with %d of %d topics", session.id, source.id,
                len(kept), len(wanted))
    return session, new_plan

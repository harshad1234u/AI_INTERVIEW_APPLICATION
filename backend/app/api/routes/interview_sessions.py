"""HTTP layer for interview sessions. Lifecycle decisions live in services/interview_state_machine."""

import logging
import uuid

import anyio.from_thread
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.gateway import ModelGateway
from app.ai.planner_agent import PlannerOutcome, propose_plan
from app.ai.providers import get_model_gateway
from app.api.routes.candidates import get_candidate
from app.db.session import get_db
from app.models import Candidate, InterviewSession
from app.schemas.interview_plan import (
    InterviewPlan,
    InterviewPlanResult,
    InterviewPlanView,
    ModelCallSummary,
    PlanRequest,
    PlanSettings,
    RulesReason,
)
from app.schemas.interview_session import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    SessionActionRequest,
)
from app.services.interview_planner import (
    PlanningNotAllowed,
    PlanRejected,
    PlanStale,
    ProjectRequired,
    fallback_plan,
    prepare_planning,
    save_plan,
)
from app.services.interview_state_machine import (
    ActiveSessionExists,
    InvalidTransition,
    ProfileNotReviewed,
    SessionEvent,
    SessionNotFound,
    apply_event,
    create_session,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["interview sessions"])

NOT_FOUND = "Interview session not found"


def get_interview_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> InterviewSession:
    # Single access point for a session by id: the ownership check goes here once auth exists.
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return session


def _commit(db: Session) -> None:
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        raise  # the app turns this into a 503
    except SQLAlchemyError as exc:
        db.rollback()
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        logger.error("Interview session write failed (%s, constraint %s)",
                     type(exc).__name__, getattr(diag, "constraint_name", None))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not save interview session"
        ) from None


@router.post(
    "/interview-sessions",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_interview_session(
    body: InterviewSessionCreate, db: Session = Depends(get_db)
) -> InterviewSession:
    candidate = get_candidate(body.candidate_id, db)
    try:
        session = create_session(db, candidate.id)
    except ActiveSessionExists as exc:
        db.rollback()
        detail = "This candidate already has an unfinished interview session"
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{detail}: {exc.session_id}. Resume it, or delete it to start again."
            if exc.session_id else f"{detail}. Please try again.",
        ) from None
    _commit(db)
    return session


@router.get("/interview-sessions/{session_id}", response_model=InterviewSessionResponse)
def read_interview_session(
    session: InterviewSession = Depends(get_interview_session),
) -> InterviewSession:
    return session


@router.get(
    "/candidates/{candidate_id}/interview-sessions",
    response_model=list[InterviewSessionResponse],
)
def list_candidate_interview_sessions(
    candidate: Candidate = Depends(get_candidate), db: Session = Depends(get_db)
) -> list[InterviewSession]:
    return list(db.scalars(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == candidate.id)
        .order_by(InterviewSession.created_at.desc(), InterviewSession.id)
    ))


@router.post(
    "/interview-sessions/{session_id}/actions", response_model=InterviewSessionResponse
)
def act_on_interview_session(
    session_id: uuid.UUID, body: SessionActionRequest, db: Session = Depends(get_db)
) -> InterviewSession:
    try:
        session = apply_event(db, session_id, SessionEvent(body.action))
    except SessionNotFound:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND) from None
    except (InvalidTransition, ProfileNotReviewed) as exc:
        db.rollback()  # nothing was written; this releases the row lock
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    _commit(db)
    return session


@router.delete("/interview-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview_session(
    session: InterviewSession = Depends(get_interview_session), db: Session = Depends(get_db)
) -> None:
    # PRD §59/§61: discarding a session deletes it. Allowed in any state.
    db.delete(session)
    _commit(db)


# ---------- planning (Phase 6) ----------


@router.post("/interview-sessions/{session_id}/plan", response_model=InterviewPlanResult)
def plan_interview_session(
    session_id: uuid.UUID,
    body: PlanRequest,
    db: Session = Depends(get_db),
    gateway: ModelGateway | None = Depends(get_model_gateway),
) -> InterviewPlanResult:
    """INTERVIEW_PLANNING -> READY with a validated plan. Never fails because AI failed: the
    deterministic plan (labelled RULES, with the reason) is used instead (PRD §30, §31)."""
    settings = PlanSettings(**body.model_dump(exclude={"use_ai"}))
    try:
        inputs = prepare_planning(db, session_id, settings)  # ends its read transaction
    except SessionNotFound:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND) from None
    except (PlanningNotAllowed, ProjectRequired) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None

    # No DB connection or lock is held from here until save_plan.
    if not body.use_ai:
        outcome = PlannerOutcome(None, RulesReason.NOT_REQUESTED)
    elif gateway is None:
        outcome = PlannerOutcome(None, RulesReason.NOT_CONFIGURED)
    else:
        # Sync route (sync DB session) calling the async gateway on the event loop.
        outcome = anyio.from_thread.run(propose_plan, gateway, inputs.settings, inputs.facts)
    try:
        plan = outcome.plan or fallback_plan(inputs.settings, inputs.facts, outcome.rules_reason)
    except PlanRejected as exc:
        # Only reachable if an approved project name collides with the fallback's own generic
        # wording; the rules still win over a plan that would mislabel the candidate's facts.
        logger.error("Fallback plan for session %s failed validation: %s", session_id, exc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Could not build an interview plan") from None

    try:
        session = save_plan(db, inputs, plan, outcome.records)
    except SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND) from None
    except (PlanningNotAllowed, PlanStale) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    _commit(db)
    return InterviewPlanResult(
        session_id=session.id,
        status=session.status,
        plan=plan,
        model_calls=[ModelCallSummary(
            request_id=r.request_id, requested_provider=r.requested_provider, provider=r.provider,
            model=r.model, fallback_used=r.fallback_used, attempts=r.attempts,
            error_type=r.error_type, latency_ms=r.latency_ms, input_tokens=r.input_tokens,
            output_tokens=r.output_tokens, total_tokens=r.total_tokens,
        ) for r in outcome.records],
    )


@router.get("/interview-sessions/{session_id}/plan", response_model=InterviewPlanView)
def read_interview_plan(
    session: InterviewSession = Depends(get_interview_session),
) -> InterviewPlanView:
    if session.plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This interview session has no plan yet")
    return InterviewPlanView(session_id=session.id, status=session.status,
                             plan=InterviewPlan.model_validate(session.plan))

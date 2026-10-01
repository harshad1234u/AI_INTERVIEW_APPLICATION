import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.resume import checked_enum

ONE_ACTIVE_SESSION_INDEX = "uq_interview_sessions_one_active_per_candidate"


class FinishReason(StrEnum):
    """Why an interview ended. Set only by the state machine, from code paths; never by a model."""

    PLAN_COMPLETED = "PLAN_COMPLETED"  # no valid topic left
    TIME_LIMIT = "TIME_LIMIT"  # deadline reached, or too little time left to start a question
    CANDIDATE_ENDED = "CANDIDATE_ENDED"  # END_INTERVIEW


class RulesReason(StrEnum):
    """Why deterministic (RULES) text was used instead of AI text. Never silent."""

    NOT_REQUESTED = "NOT_REQUESTED"  # the session has no AI consent
    NOT_CONFIGURED = "NOT_CONFIGURED"  # no AI provider on this server
    PROVIDERS_FAILED = "PROVIDERS_FAILED"  # every provider failed (timeout, auth, rate limit, ...)
    OUTPUT_REJECTED = "OUTPUT_REJECTED"  # proposals failed validation twice
    CONSENT_WITHDRAWN = "CONSENT_WITHDRAWN"  # consent withdrawn while the model was running


class InterviewStatus(StrEnum):
    """PRD §13 lifecycle, plus PAUSED from §61. Transitions live in services/interview_state_machine."""

    CREATED = "CREATED"
    PROFILE_PROCESSING = "PROFILE_PROCESSING"
    PROFILE_REVIEW = "PROFILE_REVIEW"
    INTERVIEW_PLANNING = "INTERVIEW_PLANNING"
    READY = "READY"
    ASKING = "ASKING"
    WAITING_FOR_ANSWER = "WAITING_FOR_ANSWER"
    PAUSED = "PAUSED"
    ANSWER_PROCESSING = "ANSWER_PROCESSING"
    ANSWER_EVALUATION = "ANSWER_EVALUATION"
    NEXT_DECISION = "NEXT_DECISION"
    REPORT_GENERATION = "REPORT_GENERATION"
    COMPLETED = "COMPLETED"


# States before the plan exists. Every later state (READY ... COMPLETED, PAUSED included) is reached
# only through PLAN_READY, so it always has a plan.
PRE_PLAN_STATUSES = (InterviewStatus.CREATED, InterviewStatus.PROFILE_PROCESSING,
                     InterviewStatus.PROFILE_REVIEW, InterviewStatus.INTERVIEW_PLANNING)
_PRE_PLAN_SQL = ", ".join(f"'{s.value}'" for s in PRE_PLAN_STATUSES)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        # One unfinished session per candidate (PRD §61: one session to resume, restart or discard).
        # Also makes a retried or doubled create fail cleanly instead of making a second session.
        Index(
            ONE_ACTIVE_SESSION_INDEX,
            "candidate_id",
            unique=True,
            postgresql_where=text("status <> 'COMPLETED'"),
        ),
        # Plan exists exactly when the session is past planning: no READY (or later) session
        # without a plan, and no plan saved without the move to READY.
        CheckConstraint(f"(plan IS NOT NULL) = (status NOT IN ({_PRE_PLAN_SQL}))",
                        name="plan_matches_status"),
        CheckConstraint("plan IS NULL OR jsonb_typeof(plan) = 'object'", name="plan_is_object"),
        CheckConstraint("active_seconds >= 0", name="active_seconds_not_negative"),
        # A reason only on a finished session. (Not the reverse: sessions finished before Phase 7
        # keep NULL rather than a guessed reason.)
        CheckConstraint("finish_reason IS NULL OR status IN ('REPORT_GENERATION', 'COMPLETED')",
                        name="finish_reason_only_when_finished"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    # Only the state machine writes this: never set it directly.
    status: Mapped[InterviewStatus] = mapped_column(checked_enum(InterviewStatus, "status"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # The validated InterviewPlan (schemas/interview_plan.py). Written only with PLAN_READY.
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    # The model call whose proposal became the plan; NULL for a RULES plan.
    plan_provider_call_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_calls.id", ondelete="SET NULL")
    )
    # Explicit, session-level consent to send data to an AI provider (planner and interviewer).
    # Changed only through the consent service, which also records an InterviewConsentEvent.
    ai_consent: Mapped[bool] = mapped_column(server_default=text("false"))
    # Active interview time, in database time (clock_timestamp), kept by the state machine:
    # elapsed = active_seconds + (now - active_since while running). Only PAUSE stops it.
    active_seconds: Mapped[float] = mapped_column(Double, server_default=text("0"))
    active_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finish_reason: Mapped[FinishReason | None] = mapped_column(
        checked_enum(FinishReason, "finish_reason")
    )


class InterviewConsentEvent(Base):
    """One change of a session's AI consent: when, and the resulting value. Nothing else."""

    __tablename__ = "interview_consent_events"
    __table_args__ = (Index("ix_interview_consent_events_session_id_id", "session_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE")
    )
    granted: Mapped[bool]
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

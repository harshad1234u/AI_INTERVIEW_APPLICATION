import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.resume import checked_enum

ONE_ACTIVE_SESSION_INDEX = "uq_interview_sessions_one_active_per_candidate"


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

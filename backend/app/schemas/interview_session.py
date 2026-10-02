import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.interview_session import InterviewStatus
from app.services.interview_state_machine import ClientAction


class InterviewSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: uuid.UUID


class RetryRequest(BaseModel):
    """Empty on purpose: the retried topics are decided by code from the report (Phase 10)."""

    model_config = ConfigDict(extra="forbid")


class SessionActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Client actions only: system events (PLAN_READY, FINISH, ...) fail validation with 422.
    action: ClientAction


class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    status: InterviewStatus
    created_at: datetime
    updated_at: datetime

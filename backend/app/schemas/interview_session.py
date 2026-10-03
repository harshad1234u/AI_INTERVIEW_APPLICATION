import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.interview_session import InterviewStatus
from app.services.interview_state_machine import ClientAction


class InterviewSessionCreate(BaseModel):
    """Empty on purpose: the session is for the signed-in candidate (Phase 12). A candidate_id
    sent by the client is refused (422), never trusted."""

    model_config = ConfigDict(extra="forbid")


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

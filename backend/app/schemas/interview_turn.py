"""Interviewer API contracts (Phase 7): consent, turns, answers, question history."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, StrictBool


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted: StrictBool


class ConsentChange(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    granted: bool
    changed_at: datetime


class ConsentState(BaseModel):
    session_id: uuid.UUID
    granted: bool
    changed_at: datetime | None  # of the last change; None = never changed (default: off)


class ConsentHistory(BaseModel):
    session_id: uuid.UUID
    granted: bool
    history: list[ConsentChange]

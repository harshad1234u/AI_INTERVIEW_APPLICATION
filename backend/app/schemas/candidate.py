import uuid
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.candidate import NAME_MAX_LENGTH

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH),
    AfterValidator(lambda v: " ".join(v.split())),
]
# email-validator already enforces the 254-char limit (EMAIL_MAX_LENGTH) and trims whitespace.
Email = Annotated[EmailStr, AfterValidator(str.lower)]


class CandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    name: Name


class PartialUpdate(BaseModel):
    """PATCH body: every field optional, none may be null, at least one must be sent."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("may be omitted but not null")
        return v

    @model_validator(mode="after")
    def require_a_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        return self


class CandidateUpdate(PartialUpdate):
    email: Email | None = None
    name: Name | None = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime

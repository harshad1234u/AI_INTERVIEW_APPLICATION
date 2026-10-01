import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.models.resume import (
    FACT_MAX_LENGTH,
    Extractor,
    FactCategory,
    FactSource,
    FactStatus,
    Resume,
    ResumeStatus,
)
from app.schemas.candidate import PartialUpdate
from app.services.resume_extractor import status_message

FactText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=FACT_MAX_LENGTH),
    AfterValidator(lambda v: " ".join(v.split())),
]


class SectionSummary(BaseModel):
    heading: str
    category: FactCategory | None
    page: int


class ResumeResponse(BaseModel):
    """Processing result only. Raw text and section contents are deliberately not returned."""

    id: uuid.UUID
    candidate_id: uuid.UUID
    status: ResumeStatus
    message: str | None
    page_count: int | None
    sections: list[SectionSummary]
    created_at: datetime

    @classmethod
    def from_model(cls, resume: Resume) -> Self:
        meta = resume.parsed_json
        return cls(
            id=resume.id,
            candidate_id=resume.candidate_id,
            status=resume.upload_status,
            message=status_message(meta),
            page_count=meta.get("pages"),
            sections=meta.get("sections", []),
            created_at=resume.created_at,
        )


class FactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    category: FactCategory
    fact: str
    extracted_fact: str
    source: FactSource
    source_section: str
    source_text: str
    status: FactStatus
    extracted_by: Extractor
    created_at: datetime


class AIExtractionResponse(BaseModel):
    """What happened on an AI extraction run. Provider changes are reported, never hidden."""

    request_id: str
    requested_provider: str
    provider: str  # the provider that actually answered
    model: str
    fallback_used: bool
    attempts: int
    latency_ms: int
    input_tokens: int | None  # None = the provider did not report it
    output_tokens: int | None
    total_tokens: int | None
    facts_added: int  # new PENDING_REVIEW facts
    facts_already_listed: int  # grounded, but the resume already had them
    facts_rejected: int  # failed grounding/validation; never stored


class FactUpdate(PartialUpdate):
    fact: FactText | None = None
    # PENDING_REVIEW is the extractor's state; a candidate can only approve or reject.
    status: Literal[FactStatus.APPROVED, FactStatus.REJECTED] | None = None

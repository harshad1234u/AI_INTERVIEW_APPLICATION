import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

FACT_MAX_LENGTH = 200
SECTION_MAX_LENGTH = 100
MANUAL_FACTS_MAX = 100  # per candidate (Phase 13, M3)
MANUAL_FACT_UNIQUE_INDEX = "uq_candidate_facts_manual_fact"


class ResumeStatus(StrEnum):
    # Processing is synchronous and written in one transaction, so no in-flight state is ever stored.
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"  # parser could not read the PDF
    UNSUPPORTED = "UNSUPPORTED"  # readable PDF, but no extractable text or too long


class FactStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FactCategory(StrEnum):
    SKILL = "SKILL"
    PROJECT = "PROJECT"
    EXPERIENCE = "EXPERIENCE"
    EDUCATION = "EDUCATION"
    CERTIFICATION = "CERTIFICATION"


class FactSource(StrEnum):
    RESUME = "RESUME"
    # Typed in by the candidate (PRD §18 level 1): approved, with no resume provenance.
    MANUAL = "MANUAL"


class Extractor(StrEnum):
    """Who read the fact out of the resume. Either way it is unverified until reviewed."""

    RULES = "RULES"  # deterministic Phase 3 extractor
    AI = "AI"  # ProfileAgent via the model gateway (provider/model in provider_calls)


def checked_enum(cls: type[StrEnum], name: str) -> Enum:
    # VARCHAR + CHECK constraint instead of a native PG enum: same guarantee, simpler migrations.
    # Values, not member names, are stored (they differ only for Criterion's lower-case values).
    return Enum(cls, name=name, native_enum=False, create_constraint=True, length=20,
                values_callable=lambda members: [m.value for m in members])


class Resume(Base):
    __tablename__ = "resumes"
    # Target of candidate_facts' composite FK, which pins a fact to its resume's owner.
    __table_args__ = (UniqueConstraint("id", "candidate_id", name="uq_resumes_id_candidate_id"),)
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    # Candidate-provided, unverified source material. Never interpreted as instructions.
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    upload_status: Mapped[ResumeStatus] = mapped_column(checked_enum(ResumeStatus, "upload_status"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Only used to insert facts with the resume; deletes rely on the DB cascade.
    facts: Mapped[list["CandidateFact"]] = relationship(passive_deletes=True)


class CandidateFact(Base):
    __tablename__ = "candidate_facts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resume_id", "candidate_id"],
            ["resumes.id", "resumes.candidate_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("btrim(fact) <> ''", name="fact_not_blank"),
        CheckConstraint("btrim(extracted_fact) <> ''", name="extracted_fact_not_blank"),
        # A fact is MANUAL exactly when it has no resume provenance at all (Phase 13). A manual
        # fact is approved for good; a resume fact keeps every provenance column it always had.
        CheckConstraint(
            "(source = 'MANUAL' AND resume_id IS NULL AND source_section IS NULL "
            "AND source_text IS NULL AND extracted_by IS NULL AND provider_call_id IS NULL "
            "AND status = 'APPROVED') OR "
            "(source <> 'MANUAL' AND resume_id IS NOT NULL AND source_section IS NOT NULL "
            "AND source_text IS NOT NULL AND extracted_by IS NOT NULL)",
            name="provenance_matches_source",
        ),
        # One manual fact per category and text, ignoring case (M4). Duplicates of resume facts
        # are checked by the service under the candidate row lock.
        Index(MANUAL_FACT_UNIQUE_INDEX, "candidate_id", "category", text("lower(fact)"),
              unique=True, postgresql_where=text("source = 'MANUAL'")),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(index=True)  # NULL for MANUAL
    category: Mapped[FactCategory] = mapped_column(checked_enum(FactCategory, "category"))
    # Current value: the extraction, or the candidate's edit of it.
    fact: Mapped[str] = mapped_column(String(FACT_MAX_LENGTH))
    # What the extractor produced; never changes, so edits stay auditable.
    extracted_fact: Mapped[str] = mapped_column(String(FACT_MAX_LENGTH))
    source: Mapped[FactSource] = mapped_column(checked_enum(FactSource, "source"))
    source_section: Mapped[str | None] = mapped_column(String(SECTION_MAX_LENGTH))
    # The resume line the fact was taken from.
    source_text: Mapped[str | None] = mapped_column(Text)
    # Every fact starts unreviewed; only an explicit candidate action changes it.
    status: Mapped[FactStatus] = mapped_column(
        checked_enum(FactStatus, "status"), server_default=FactStatus.PENDING_REVIEW.value
    )
    # NULL for MANUAL: nobody extracted it.
    extracted_by: Mapped[Extractor | None] = mapped_column(
        checked_enum(Extractor, "extracted_by"), server_default=Extractor.RULES.value
    )
    # The model call that produced an AI fact (kept NULL if call metadata is ever purged).
    provider_call_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_calls.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

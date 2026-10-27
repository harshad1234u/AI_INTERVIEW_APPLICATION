import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.gateway import CallRecord, ErrorKind, ModelCapability
from app.db.base import Base
from app.models.resume import checked_enum


class ProviderCall(Base):
    """One model-gateway call: operational/cost metadata only.

    Deliberately no prompt, resume text, model output or candidate link: this table must never
    become a second copy of personal data.
    """

    __tablename__ = "provider_calls"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_id: Mapped[str] = mapped_column(String(32), index=True)  # correlates with logs
    capability: Mapped[ModelCapability] = mapped_column(checked_enum(ModelCapability, "capability"))
    requested_provider: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str | None] = mapped_column(String(20))  # who answered; NULL = nobody
    model: Mapped[str | None] = mapped_column(String(200))
    succeeded: Mapped[bool]
    attempts: Mapped[int]
    fallback_used: Mapped[bool]
    error_type: Mapped[ErrorKind | None] = mapped_column(checked_enum(ErrorKind, "error_type"))
    latency_ms: Mapped[int]
    input_tokens: Mapped[int | None]  # as reported by the provider; NULL = not reported
    output_tokens: Mapped[int | None]
    total_tokens: Mapped[int | None]
    provider_request_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @classmethod
    def from_record(cls, record: CallRecord) -> "ProviderCall":
        return cls(
            id=uuid.uuid4(),  # known before INSERT so facts can reference it in the same flush
            request_id=record.request_id,
            capability=record.capability,
            requested_provider=record.requested_provider,
            provider=record.provider,
            model=record.model,
            succeeded=record.succeeded,
            attempts=record.attempts,
            fallback_used=record.fallback_used,
            error_type=record.error_type,
            latency_ms=record.latency_ms,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
            provider_request_id=(record.provider_request_id or "")[:200] or None,
        )

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

NAME_MAX_LENGTH = 200
EMAIL_MAX_LENGTH = 254  # RFC 5321 path limit
EMAIL_UNIQUE_CONSTRAINT = "uq_candidates_email"


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
    )
    # Fetch server-generated id/created_at on INSERT via RETURNING.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

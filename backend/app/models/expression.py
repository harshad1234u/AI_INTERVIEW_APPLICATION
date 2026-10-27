import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.resume import checked_enum

# The face-expression model's classes (face-api.js expression net), counted per question.
EXPRESSIONS = ("neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised")
MAX_SAMPLES = 10_000  # one sample a second for far longer than any question stays open


class ExpressionStatus(StrEnum):
    ANALYZED = "ANALYZED"  # the camera was on and the browser model ran for this question
    UNAVAILABLE = "UNAVAILABLE"  # the candidate enabled it, but it failed (camera, model, device)


class QuestionExpressionObservation(Base):
    """Optional, experimental: how often each facial-expression class was detected in the
    candidate's own browser while one question was open. Counts only: no image, frame, video,
    landmark, score or timestamp ever reaches the server. Never read by the interviewer, the
    evaluator or any score; shown in the report as a plain observation."""

    __tablename__ = "question_expression_observations"
    __table_args__ = (
        *(CheckConstraint(f"{name} BETWEEN 0 AND {MAX_SAMPLES}", name=f"{name}_range")
          for name in (*EXPRESSIONS, "no_face", "multiple_faces")),
        CheckConstraint("status = 'ANALYZED' OR (neutral + happy + sad + angry + fearful + "
                        "disgusted + surprised + no_face + multiple_faces) = 0",
                        name="unavailable_has_no_counts"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[ExpressionStatus] = mapped_column(checked_enum(ExpressionStatus, "status"))
    neutral: Mapped[int] = mapped_column(Integer)
    happy: Mapped[int] = mapped_column(Integer)
    sad: Mapped[int] = mapped_column(Integer)
    angry: Mapped[int] = mapped_column(Integer)
    fearful: Mapped[int] = mapped_column(Integer)
    disgusted: Mapped[int] = mapped_column(Integer)
    surprised: Mapped[int] = mapped_column(Integer)
    no_face: Mapped[int] = mapped_column(Integer)  # sampled, but no face was found
    multiple_faces: Mapped[int] = mapped_column(Integer)  # sampled, more than one face: skipped
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

"""Interviewer API contracts (Phase 7): consent, turns, answers, question history, and the only
shapes a model may return for question wording."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StrictBool, StringConstraints

from app.models.interview_question import AnswerKind, EvaluationStatus, QuestionKind, QuestionSource
from app.models.interview_session import FinishReason, InterviewStatus, RulesReason
from app.schemas.interview_plan import (
    Competency,
    Difficulty,
    ModelCallSummary,
    QuestionType,
    TopicBasis,
)

# ---------- consent ----------


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


# ---------- model output: wording only ----------

ModelQuestion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class FollowUpWording(BaseModel):
    """No action, status, event, id, topic, competency, difficulty, score, finish or reason field:
    a model can only word a follow-up that code already chose."""

    model_config = ConfigDict(extra="forbid")

    question: ModelQuestion
    # The answer phrase the question is about (must also be plan vocabulary; checked by code).
    anchor: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class RephraseWording(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: ModelQuestion


# ---------- requests ----------


class NextQuestionRequest(BaseModel):
    """Empty on purpose: the client asks for the next question, code decides what it is."""

    model_config = ConfigDict(extra="forbid")


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID
    kind: AnswerKind
    # Length is checked explicitly by the route (exact 422 message, D5), not here.
    text: str | None = None


# ---------- responses ----------


class Evaluation(BaseModel):
    status: EvaluationStatus  # NOT_EVALUATED: stored, not evaluated (Phase 8 evaluates)


class AnswerView(BaseModel):
    kind: AnswerKind
    text: str | None
    answered_at: datetime
    evaluation: Evaluation


class QuestionView(BaseModel):
    id: uuid.UUID
    seq: int
    topic_position: int
    topic: str
    competency: Competency
    question_type: QuestionType
    difficulty: Difficulty
    basis: TopicBasis
    kind: QuestionKind
    followup_index: int
    rephrase_index: int
    text: str  # untrusted text: render as plain text
    source: QuestionSource
    rules_reason: RulesReason | None
    asked_at: datetime
    answer: AnswerView | None


class Progress(BaseModel):
    topics_total: int
    time_remaining_seconds: int  # display only: floor of the exact value, never below 0
    deadline_reached: bool


class TurnResult(BaseModel):
    session_id: uuid.UUID
    status: InterviewStatus
    finish_reason: FinishReason | None
    ai_consent: bool
    question: QuestionView | None  # None: the interview is over (see finish_reason)
    progress: Progress
    model_calls: list[ModelCallSummary]  # empty when no model was asked


class AnswerResult(BaseModel):
    session_id: uuid.UUID
    status: InterviewStatus
    question: QuestionView


class QuestionHistory(BaseModel):
    session_id: uuid.UUID
    status: InterviewStatus
    finish_reason: FinishReason | None
    progress: Progress | None  # None before the interview has a plan
    questions: list[QuestionView]

"""Interview plan contracts (PRD §8, §14, §42): planning settings, the model's proposal, the stored plan.

Three different shapes on purpose:
- PlanSettings: what the client chooses. Closed sets only, so no client free text reaches a prompt.
  Whether a model may be asked is the session's AI consent (PUT .../ai-consent), not a field here.
- PlanProposal: the only thing a model may return. No status, approval, score, id, difficulty or
  fact fields: it can cite approved facts by ref, never add or change one.
- InterviewPlan: what the application stores after validation. Built by code, never by the model.
"""

import uuid
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# RulesReason (why a RULES plan was used) is shared with interview questions, so it lives with the
# session model; it is re-exported here.
from app.models.interview_session import InterviewStatus, RulesReason  # noqa: F401
from app.models.resume import FACT_MAX_LENGTH, FactCategory

MINUTES_PER_TOPIC = 3  # duration // 3 = topic budget; 15 min -> 5 topics, as in the PRD §58 example
MAX_TOPICS = 45 // MINUTES_PER_TOPIC


class TargetRole(StrEnum):
    # Software Development
    SOFTWARE_ENGINEER = "SOFTWARE_ENGINEER"
    SOFTWARE_DEVELOPER_INTERN = "SOFTWARE_DEVELOPER_INTERN"
    FRONTEND_DEVELOPER = "FRONTEND_DEVELOPER"
    BACKEND_DEVELOPER = "BACKEND_DEVELOPER"
    FULL_STACK_DEVELOPER = "FULL_STACK_DEVELOPER"
    PYTHON_DEVELOPER = "PYTHON_DEVELOPER"
    JAVA_DEVELOPER = "JAVA_DEVELOPER"
    ANDROID_DEVELOPER = "ANDROID_DEVELOPER"
    # AI and Data
    AI_ML_ENGINEER = "AI_ML_ENGINEER"
    GENERATIVE_AI_ENGINEER = "GENERATIVE_AI_ENGINEER"
    DATA_ANALYST = "DATA_ANALYST"
    DATA_SCIENTIST = "DATA_SCIENTIST"
    DATA_ENGINEER = "DATA_ENGINEER"
    # Cybersecurity
    CYBERSECURITY_ANALYST = "CYBERSECURITY_ANALYST"
    SOC_ANALYST = "SOC_ANALYST"
    PENETRATION_TESTER = "PENETRATION_TESTER"
    SECURITY_ENGINEER = "SECURITY_ENGINEER"
    # Cloud and DevOps
    CLOUD_ENGINEER = "CLOUD_ENGINEER"
    DEVOPS_ENGINEER = "DEVOPS_ENGINEER"
    SITE_RELIABILITY_ENGINEER = "SITE_RELIABILITY_ENGINEER"
    # Other Technical Roles
    QA_TEST_ENGINEER = "QA_TEST_ENGINEER"
    AUTOMATION_TEST_ENGINEER = "AUTOMATION_TEST_ENGINEER"
    DATABASE_ADMINISTRATOR = "DATABASE_ADMINISTRATOR"
    NETWORK_ENGINEER = "NETWORK_ENGINEER"
    MOBILE_APP_DEVELOPER = "MOBILE_APP_DEVELOPER"
    # General and Professional
    HR_BEHAVIORAL = "HR_BEHAVIORAL"
    BUSINESS_ANALYST = "BUSINESS_ANALYST"
    PRODUCT_MANAGER = "PRODUCT_MANAGER"
    TECHNICAL_SUPPORT_ENGINEER = "TECHNICAL_SUPPORT_ENGINEER"


class ExperienceLevel(StrEnum):
    """Self-reported by the candidate (PRD §4 user groups). Never a verified candidate fact."""

    STUDENT = "STUDENT"
    FRESH_GRADUATE = "FRESH_GRADUATE"
    ENTRY_LEVEL = "ENTRY_LEVEL"
    INTERNSHIP_APPLICANT = "INTERNSHIP_APPLICANT"


class InterviewMode(StrEnum):
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    PROJECT_DEEP_DIVE = "PROJECT_DEEP_DIVE"
    MIXED = "MIXED"


class Difficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Competency(StrEnum):
    # Original competencies (Software Developer Intern).
    PROGRAMMING_FUNDAMENTALS = "programming_fundamentals"
    DATA_STRUCTURES = "data_structures"
    DATABASE = "database"
    WEB_DEVELOPMENT = "web_development"
    PROJECT_UNDERSTANDING = "project_understanding"
    BEHAVIORAL = "behavioral"
    HR = "hr"
    # Role-specific competencies.
    API_DESIGN = "api_design"
    SYSTEM_DESIGN = "system_design"
    TESTING_QA = "testing_qa"
    PYTHON_LANGUAGE = "python_language"
    JAVA_LANGUAGE = "java_language"
    MOBILE_DEVELOPMENT = "mobile_development"
    ML_FUNDAMENTALS = "ml_fundamentals"
    DATA_ANALYSIS = "data_analysis"
    DATA_ENGINEERING = "data_engineering"
    SECURITY_FUNDAMENTALS = "security_fundamentals"
    NETWORK_SECURITY = "network_security"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    DEVOPS_PRACTICES = "devops_practices"
    NETWORKING = "networking"
    BUSINESS_ANALYSIS = "business_analysis"
    PRODUCT_MANAGEMENT = "product_management"
    TECHNICAL_SUPPORT = "technical_support"
    PROFESSIONAL_SKILLS = "professional_skills"


class QuestionType(StrEnum):
    """The §42 groups. Derived from the competency by code, never chosen by the model."""

    TECHNICAL = "TECHNICAL"
    PROJECT = "PROJECT"
    BEHAVIORAL = "BEHAVIORAL"
    HR = "HR"


class TopicBasis(StrEnum):
    """Derived from citations by code. GENERIC topics say nothing about the candidate."""

    GENERIC = "GENERIC"  # a domain/behavioral question; no candidate fact behind it
    CANDIDATE_FACT = "CANDIDATE_FACT"  # about the cited, candidate-approved facts


class PlanSource(StrEnum):
    AI = "AI"  # model proposal that passed validation
    RULES = "RULES"  # deterministic plan (same validation)


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TopicText = Annotated[Text, StringConstraints(max_length=FACT_MAX_LENGTH + 50)]
QuestionText = Annotated[Text, StringConstraints(max_length=FACT_MAX_LENGTH + 100)]
ConceptText = Annotated[Text, StringConstraints(max_length=80)]
FactRef = Annotated[str, StringConstraints(pattern=r"^F[1-9][0-9]{0,3}$")]


class PlanSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_role: TargetRole = TargetRole.SOFTWARE_DEVELOPER_INTERN
    experience_level: ExperienceLevel
    mode: InterviewMode
    difficulty: Difficulty
    duration_minutes: Literal[15, 30, 45]


# ---------- model proposal (the only shape a model may return) ----------


class TopicProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competency: Competency
    topic: TopicText
    fact_refs: list[FactRef] = Field(max_length=3)
    question_templates: list[QuestionText] = Field(min_length=1, max_length=3)
    expected_concepts: list[ConceptText] = Field(max_length=8)


class PlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topics: list[TopicProposal] = Field(min_length=1, max_length=MAX_TOPICS)


# ---------- stored plan ----------


class FactSnapshot(BaseModel):
    """An APPROVED fact as it was when the plan was made. Plan context only: never a new fact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: uuid.UUID
    category: FactCategory
    fact: str


class PlannedTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=1)
    competency: Competency
    question_type: QuestionType
    difficulty: Difficulty
    basis: TopicBasis
    topic: TopicText
    question_templates: list[QuestionText] = Field(min_length=1, max_length=3)
    expected_concepts: list[ConceptText] = Field(max_length=8)
    facts: list[FactSnapshot] = Field(max_length=3)


class InterviewPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    source: PlanSource
    rules_reason: RulesReason | None
    settings: PlanSettings
    competencies: list[Competency]
    # §42 groups the mode includes but the plan leaves out, e.g. PROJECT in MIXED mode when the
    # candidate has no approved project: nothing is invented to fill it.
    omitted_groups: list[QuestionType]
    topics: list[PlannedTopic] = Field(min_length=1, max_length=MAX_TOPICS)


# ---------- API responses ----------


class ModelCallSummary(BaseModel):
    """Operational metadata of one gateway call. No prompt or output content."""

    request_id: str
    requested_provider: str | None
    provider: str | None  # None = no provider answered
    model: str | None
    fallback_used: bool
    attempts: int
    error_type: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class InterviewPlanView(BaseModel):
    session_id: uuid.UUID
    status: InterviewStatus
    plan: InterviewPlan


class InterviewPlanResult(InterviewPlanView):
    model_calls: list[ModelCallSummary]  # empty when no model was asked

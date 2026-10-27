"""Interview Planner (PRD §8): deterministic catalog, validation, fallback plan and persistence.

The model only proposes (app/ai/planner_agent.py). This module decides:
- what a model may see: APPROVED facts only (PRD §18 levels 1-2), under short refs;
- whether a proposal is acceptable: build_plan() applies every business, grounding and safety rule,
  to model proposals and to the deterministic fallback alike. Nothing unvalidated is ever stored;
- how it is stored: save_plan() writes the plan together with PLAN_READY under the session lock.

Transaction contract: prepare_planning() ends its read transaction, so no connection or row lock is
held while a model is called. save_plan() flushes and the caller commits; on a lost race it rolls
back, records the model calls on their own, and raises.

Consent (PRD §48, D2b): the session's ai_consent decides whether a model may be asked at all
(prepare_planning reads it) and is read again under the lock in save_plan: an AI plan made while
consent was being withdrawn is discarded, and the deterministic plan is stored instead.

Model calls are not exactly-once: two concurrent requests for the same session can both call a
model. The lock + status re-check in save_plan() lets exactly one plan persist.
"""

import logging
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import CallRecord
from app.models import CandidateFact, InterviewSession, ProviderCall
from app.models.interview_session import InterviewStatus
from app.models.resume import FactCategory, FactStatus
from app.schemas.interview_plan import (
    MINUTES_PER_TOPIC,
    Competency,
    FactSnapshot,
    InterviewMode,
    InterviewPlan,
    PlannedTopic,
    PlanProposal,
    PlanSettings,
    PlanSource,
    QuestionType,
    RulesReason,
    TargetRole,
    TopicBasis,
    TopicProposal,
)
from app.services.interview_state_machine import (
    InvalidTransition,
    SessionEvent,
    SessionNotFound,
    apply_event,
)

logger = logging.getLogger(__name__)
C, Q, M = Competency, QuestionType, InterviewMode

# ---------- catalog: the PRD §26 planner "tools", as data ----------

R = TargetRole
ROLE_LABELS = {
    R.SOFTWARE_ENGINEER: "Software Engineer",
    R.SOFTWARE_DEVELOPER_INTERN: "Software Developer Intern",
    R.FRONTEND_DEVELOPER: "Frontend Developer",
    R.BACKEND_DEVELOPER: "Backend Developer",
    R.FULL_STACK_DEVELOPER: "Full-Stack Developer",
    R.PYTHON_DEVELOPER: "Python Developer",
    R.JAVA_DEVELOPER: "Java Developer",
    R.ANDROID_DEVELOPER: "Android Developer",
    R.AI_ML_ENGINEER: "AI/ML Engineer",
    R.GENERATIVE_AI_ENGINEER: "Generative AI Engineer",
    R.DATA_ANALYST: "Data Analyst",
    R.DATA_SCIENTIST: "Data Scientist",
    R.DATA_ENGINEER: "Data Engineer",
    R.CYBERSECURITY_ANALYST: "Cybersecurity Analyst",
    R.SOC_ANALYST: "SOC Analyst",
    R.PENETRATION_TESTER: "Penetration Tester",
    R.SECURITY_ENGINEER: "Security Engineer",
    R.CLOUD_ENGINEER: "Cloud Engineer",
    R.DEVOPS_ENGINEER: "DevOps Engineer",
    R.SITE_RELIABILITY_ENGINEER: "Site Reliability Engineer",
    R.QA_TEST_ENGINEER: "QA / Test Engineer",
    R.AUTOMATION_TEST_ENGINEER: "Automation Test Engineer",
    R.DATABASE_ADMINISTRATOR: "Database Administrator",
    R.NETWORK_ENGINEER: "Network Engineer",
    R.MOBILE_APP_DEVELOPER: "Mobile App Developer",
    R.HR_BEHAVIORAL: "HR / Behavioral Interview",
    R.BUSINESS_ANALYST: "Business Analyst",
    R.PRODUCT_MANAGER: "Product Manager",
    R.TECHNICAL_SUPPORT_ENGINEER: "Technical Support Engineer",
}

# Each role's competencies used by the planner. PROJECT_UNDERSTANDING, BEHAVIORAL and HR are
# included for every role so that MIXED mode always has all four groups. The first competencies
# listed are the role-specific technical ones; the shared ones follow.
_CORE = (C.PROJECT_UNDERSTANDING, C.BEHAVIORAL, C.HR)

ROLE_COMPETENCIES: dict[TargetRole, tuple[Competency, ...]] = {
    # Software Development
    R.SOFTWARE_ENGINEER: (C.PROGRAMMING_FUNDAMENTALS, C.DATA_STRUCTURES, C.DATABASE,
                          C.WEB_DEVELOPMENT, C.SYSTEM_DESIGN, *_CORE),
    R.SOFTWARE_DEVELOPER_INTERN: (C.PROGRAMMING_FUNDAMENTALS, C.DATA_STRUCTURES, C.DATABASE,
                                  C.WEB_DEVELOPMENT, *_CORE),
    R.FRONTEND_DEVELOPER: (C.WEB_DEVELOPMENT, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.BACKEND_DEVELOPER: (C.API_DESIGN, C.DATABASE, C.PROGRAMMING_FUNDAMENTALS,
                          C.SYSTEM_DESIGN, *_CORE),
    R.FULL_STACK_DEVELOPER: (C.WEB_DEVELOPMENT, C.API_DESIGN, C.DATABASE,
                             C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.PYTHON_DEVELOPER: (C.PYTHON_LANGUAGE, C.DATA_STRUCTURES, C.DATABASE,
                         C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.JAVA_DEVELOPER: (C.JAVA_LANGUAGE, C.DATA_STRUCTURES, C.DATABASE,
                       C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.ANDROID_DEVELOPER: (C.MOBILE_DEVELOPMENT, C.PROGRAMMING_FUNDAMENTALS, C.DATABASE, *_CORE),
    # AI and Data
    R.AI_ML_ENGINEER: (C.ML_FUNDAMENTALS, C.PYTHON_LANGUAGE, C.DATA_STRUCTURES,
                       C.SYSTEM_DESIGN, *_CORE),
    R.GENERATIVE_AI_ENGINEER: (C.ML_FUNDAMENTALS, C.PYTHON_LANGUAGE, C.SYSTEM_DESIGN,
                               C.API_DESIGN, *_CORE),
    R.DATA_ANALYST: (C.DATA_ANALYSIS, C.DATABASE, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.DATA_SCIENTIST: (C.ML_FUNDAMENTALS, C.DATA_ANALYSIS, C.PYTHON_LANGUAGE, *_CORE),
    R.DATA_ENGINEER: (C.DATA_ENGINEERING, C.DATABASE, C.PROGRAMMING_FUNDAMENTALS,
                      C.SYSTEM_DESIGN, *_CORE),
    # Cybersecurity
    R.CYBERSECURITY_ANALYST: (C.SECURITY_FUNDAMENTALS, C.NETWORK_SECURITY,
                              C.NETWORKING, *_CORE),
    R.SOC_ANALYST: (C.SECURITY_FUNDAMENTALS, C.NETWORK_SECURITY, C.NETWORKING, *_CORE),
    R.PENETRATION_TESTER: (C.SECURITY_FUNDAMENTALS, C.NETWORK_SECURITY,
                           C.NETWORKING, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.SECURITY_ENGINEER: (C.SECURITY_FUNDAMENTALS, C.NETWORK_SECURITY,
                          C.SYSTEM_DESIGN, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    # Cloud and DevOps
    R.CLOUD_ENGINEER: (C.CLOUD_INFRASTRUCTURE, C.NETWORKING, C.SYSTEM_DESIGN, *_CORE),
    R.DEVOPS_ENGINEER: (C.DEVOPS_PRACTICES, C.CLOUD_INFRASTRUCTURE, C.SYSTEM_DESIGN, *_CORE),
    R.SITE_RELIABILITY_ENGINEER: (C.DEVOPS_PRACTICES, C.CLOUD_INFRASTRUCTURE,
                                  C.SYSTEM_DESIGN, C.NETWORKING, *_CORE),
    # Other Technical Roles
    R.QA_TEST_ENGINEER: (C.TESTING_QA, C.PROGRAMMING_FUNDAMENTALS, C.DATABASE, *_CORE),
    R.AUTOMATION_TEST_ENGINEER: (C.TESTING_QA, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.DATABASE_ADMINISTRATOR: (C.DATABASE, C.SYSTEM_DESIGN, C.PROGRAMMING_FUNDAMENTALS, *_CORE),
    R.NETWORK_ENGINEER: (C.NETWORKING, C.SECURITY_FUNDAMENTALS, C.SYSTEM_DESIGN, *_CORE),
    R.MOBILE_APP_DEVELOPER: (C.MOBILE_DEVELOPMENT, C.PROGRAMMING_FUNDAMENTALS,
                             C.DATABASE, *_CORE),
    # General and Professional
    R.HR_BEHAVIORAL: (C.PROFESSIONAL_SKILLS, *_CORE),
    R.BUSINESS_ANALYST: (C.BUSINESS_ANALYSIS, C.DATABASE, C.DATA_ANALYSIS, *_CORE),
    R.PRODUCT_MANAGER: (C.PRODUCT_MANAGEMENT, C.SYSTEM_DESIGN, C.BUSINESS_ANALYSIS, *_CORE),
    R.TECHNICAL_SUPPORT_ENGINEER: (C.TECHNICAL_SUPPORT, C.NETWORKING,
                                   C.DATABASE, *_CORE),
}

GROUP = {
    C.PROGRAMMING_FUNDAMENTALS: Q.TECHNICAL, C.DATA_STRUCTURES: Q.TECHNICAL, C.DATABASE: Q.TECHNICAL,
    C.WEB_DEVELOPMENT: Q.TECHNICAL, C.PROJECT_UNDERSTANDING: Q.PROJECT, C.BEHAVIORAL: Q.BEHAVIORAL,
    C.HR: Q.HR,
    # New competencies all map to the TECHNICAL group.
    C.API_DESIGN: Q.TECHNICAL, C.SYSTEM_DESIGN: Q.TECHNICAL, C.TESTING_QA: Q.TECHNICAL,
    C.PYTHON_LANGUAGE: Q.TECHNICAL, C.JAVA_LANGUAGE: Q.TECHNICAL,
    C.MOBILE_DEVELOPMENT: Q.TECHNICAL, C.ML_FUNDAMENTALS: Q.TECHNICAL,
    C.DATA_ANALYSIS: Q.TECHNICAL, C.DATA_ENGINEERING: Q.TECHNICAL,
    C.SECURITY_FUNDAMENTALS: Q.TECHNICAL, C.NETWORK_SECURITY: Q.TECHNICAL,
    C.CLOUD_INFRASTRUCTURE: Q.TECHNICAL, C.DEVOPS_PRACTICES: Q.TECHNICAL,
    C.NETWORKING: Q.TECHNICAL, C.BUSINESS_ANALYSIS: Q.TECHNICAL,
    C.PRODUCT_MANAGEMENT: Q.TECHNICAL, C.TECHNICAL_SUPPORT: Q.TECHNICAL,
    C.PROFESSIONAL_SKILLS: Q.TECHNICAL,
}
LABELS = {
    C.PROGRAMMING_FUNDAMENTALS: "Programming Fundamentals", C.DATA_STRUCTURES: "Data Structures",
    C.DATABASE: "Database", C.WEB_DEVELOPMENT: "Web Development",
    C.PROJECT_UNDERSTANDING: "Project Understanding", C.BEHAVIORAL: "Behavioral", C.HR: "HR",
    C.API_DESIGN: "API Design", C.SYSTEM_DESIGN: "System Design", C.TESTING_QA: "Testing & QA",
    C.PYTHON_LANGUAGE: "Python", C.JAVA_LANGUAGE: "Java",
    C.MOBILE_DEVELOPMENT: "Mobile Development", C.ML_FUNDAMENTALS: "ML Fundamentals",
    C.DATA_ANALYSIS: "Data Analysis", C.DATA_ENGINEERING: "Data Engineering",
    C.SECURITY_FUNDAMENTALS: "Security Fundamentals", C.NETWORK_SECURITY: "Network Security",
    C.CLOUD_INFRASTRUCTURE: "Cloud Infrastructure", C.DEVOPS_PRACTICES: "DevOps Practices",
    C.NETWORKING: "Networking", C.BUSINESS_ANALYSIS: "Business Analysis",
    C.PRODUCT_MANAGEMENT: "Product Management", C.TECHNICAL_SUPPORT: "Technical Support",
    C.PROFESSIONAL_SKILLS: "Professional Skills",
}
# PRD §42: the groups each mode is made of, in interview order.
MODE_GROUPS = {
    M.TECHNICAL: (Q.TECHNICAL,),
    M.BEHAVIORAL: (Q.BEHAVIORAL,),
    M.PROJECT_DEEP_DIVE: (Q.PROJECT,),
    M.MIXED: (Q.TECHNICAL, Q.PROJECT, Q.BEHAVIORAL, Q.HR),
}
# PRD §42 focus lists. For project and behavioral topics these ARE the expected concepts: a model
# must not turn a guess about the candidate ("their project uses ONNX") into an expected concept.
FOCUS = {
    Q.TECHNICAL: ("concepts", "reasoning", "implementation", "trade-offs"),
    Q.PROJECT: ("architecture", "technologies", "decisions", "challenges", "debugging", "trade-offs"),
    Q.BEHAVIORAL: ("experiences", "decisions", "conflict", "teamwork", "learning"),
}
CODE_SET_CONCEPTS = (Q.PROJECT, Q.BEHAVIORAL)
# PRD §19: never plan questions about these. Checked in the plan's own wording (cited facts excluded).
SENSITIVE = re.compile(r"\b(?:gender|religion|religious|caste|marital|photograph)\b", re.IGNORECASE)
# Facts sent to a model, projects first. ponytail: a hard cap, not a relevance ranking.
MAX_PLAN_FACTS = 200
CATEGORY_ORDER = (FactCategory.PROJECT, FactCategory.SKILL, FactCategory.EXPERIENCE,
                  FactCategory.CERTIFICATION, FactCategory.EDUCATION)

# Deterministic fallback content (PRD §30, §31). Generic questions presume no candidate fact;
# project questions come from the PRD's own examples (§8, §58) and only name approved projects.
# One curated question per technical area (PRD §32), each about its own concept, so that no two
# are §33 duplicates of each other: a shared frame made them so, and topics were skipped.
TECHNICAL_QUESTIONS = {
    C.PROGRAMMING_FUNDAMENTALS: "How would you explain recursion to someone new to programming, "
                                "and when would a loop be the better choice?",
    C.DATA_STRUCTURES: "When would you pick a hash map instead of an array, and what does that "
                       "choice cost?",
    C.DATABASE: "Why do databases use indexes, and what is the downside of adding too many of "
                "them?",
    C.WEB_DEVELOPMENT: "What happens between typing a web address into a browser and the page "
                       "appearing on screen?",
    C.API_DESIGN: "What makes a REST API well-designed, and how would you handle errors "
                  "in responses?",
    C.SYSTEM_DESIGN: "How would you design a URL shortening service, and what trade-offs "
                     "would you consider?",
    C.TESTING_QA: "What is the difference between unit tests and integration tests, and when "
                  "would you use each?",
    C.PYTHON_LANGUAGE: "How do Python generators work, and when would you choose one over "
                       "a list comprehension?",
    C.JAVA_LANGUAGE: "What is the difference between an abstract class and an interface in "
                     "Java, and when would you use each?",
    C.MOBILE_DEVELOPMENT: "What are the key differences between native and cross-platform "
                          "mobile development approaches?",
    C.ML_FUNDAMENTALS: "What is overfitting in machine learning, and what techniques help "
                       "prevent it?",
    C.DATA_ANALYSIS: "Walk through how you would clean and prepare a messy dataset for "
                     "analysis.",
    C.DATA_ENGINEERING: "What is the difference between a data lake and a data warehouse, "
                        "and when would you use each?",
    C.SECURITY_FUNDAMENTALS: "What is the CIA triad in information security, and how does "
                             "each part apply to a web application?",
    C.NETWORK_SECURITY: "How does a firewall protect a network, and what is the difference "
                        "between stateful and stateless inspection?",
    C.CLOUD_INFRASTRUCTURE: "What are the key differences between IaaS, PaaS and SaaS, "
                            "and when would you choose each?",
    C.DEVOPS_PRACTICES: "What is a CI/CD pipeline, and what are the benefits of automating "
                        "the build and deployment process?",
    C.NETWORKING: "How does DNS resolution work from a browser request to the response, "
                  "and what can go wrong?",
    C.BUSINESS_ANALYSIS: "How would you gather and prioritize requirements for a new "
                         "software feature from multiple stakeholders?",
    C.PRODUCT_MANAGEMENT: "How would you decide which features to include in the next release "
                          "of a product?",
    C.TECHNICAL_SUPPORT: "How would you troubleshoot a user reporting that an application "
                         "is running slowly?",
    C.PROFESSIONAL_SKILLS: "How do you approach communicating complex or difficult information "
                           "to non-technical stakeholders?",
}
PROJECT_QUESTIONS = ("Explain the architecture of {project}.",
                     "What would you improve in {project}?")
BEHAVIORAL_TOPICS = (  # one per §42 behavioral focus area
    ("Teamwork", "Describe a time you worked in a team. What was your role?"),
    ("Conflict", "Describe a disagreement while working with others and how it was resolved."),
    ("Decisions", "Describe a decision you had to make and how you made it."),
    ("Learning", "Describe something you had to learn quickly and how you approached it."),
    ("Experiences", "Describe an experience that taught you something important."),
)
HR_TOPIC = ("Motivation", "What interests you about a {role} role?")


# ---------- errors ----------


class PlanningNotAllowed(Exception):
    def __init__(self, status: object) -> None:
        super().__init__(f"Cannot plan an interview session in {status}.")
        self.status = status


class ProjectRequired(Exception):
    def __init__(self) -> None:
        super().__init__(
            "A project deep dive needs at least one approved project. Approve a project in your "
            "resume review, or choose another interview mode."
        )


class PlanStale(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Your approved profile changed while the plan was being made. Please try again."
        )


class PlanRejected(Exception):
    """A proposal broke a rule. Carries rule codes only, never content."""

    def __init__(self, codes: set[str]) -> None:
        super().__init__(", ".join(sorted(codes)))
        self.codes = frozenset(codes)


# ---------- rules ----------


def topic_budget(settings: PlanSettings) -> int:
    return settings.duration_minutes // MINUTES_PER_TOPIC


def plan_groups(
    settings: PlanSettings, facts: list[FactSnapshot]
) -> tuple[list[QuestionType], list[QuestionType]]:
    """(required groups, omitted groups). The PROJECT group needs an approved project: nothing is
    invented to fill it. Project deep dive can't work without one; MIXED leaves it out, openly."""
    groups = list(MODE_GROUPS[settings.mode])
    if Q.PROJECT in groups and not any(f.category == FactCategory.PROJECT for f in facts):
        if settings.mode == M.PROJECT_DEEP_DIVE:
            raise ProjectRequired()
        groups.remove(Q.PROJECT)
        return groups, [Q.PROJECT]
    return groups, []


def allowed_competencies(settings: PlanSettings, groups: list[QuestionType]) -> list[Competency]:
    return [c for c in ROLE_COMPETENCIES[settings.target_role] if GROUP[c] in groups]


def fact_refs(facts: list[FactSnapshot]) -> dict[str, FactSnapshot]:
    """Short refs (F1, F2, ...) instead of UUIDs, which models tend to mangle."""
    return {f"F{i}": fact for i, fact in enumerate(facts, 1)}


def phrase_pattern(text: str) -> re.Pattern[str]:
    # Whole-phrase, case-insensitive; works for "C++" and "C#" too, where \b would not.
    return re.compile(rf"(?<!\w){re.escape(text)}(?!\w)", re.IGNORECASE)


def mentions(text: str, phrase: str) -> bool:
    return phrase_pattern(phrase).search(text) is not None


def own_words(text: str, phrases: list[str]) -> str:
    """The text minus the given phrases (longest first): what the planner itself wrote."""
    for phrase in sorted(phrases, key=len, reverse=True):
        text = phrase_pattern(phrase).sub(" ", text)
    return text


def _key(text: str) -> str:
    return " ".join(text.casefold().split()).rstrip(".?! ")


def build_plan(
    proposal: PlanProposal,
    settings: PlanSettings,
    facts: list[FactSnapshot],
    *,
    source: PlanSource,
    rules_reason: RulesReason | None = None,
) -> InterviewPlan:
    """Validate a proposal and build the plan to store, or raise PlanRejected with rule codes.

    The same function judges model proposals and the deterministic fallback.
    """
    groups, omitted = plan_groups(settings, facts)
    allowed = set(allowed_competencies(settings, groups))
    refs = fact_refs(facts)
    projects = [f.fact for f in facts if f.category == FactCategory.PROJECT]
    codes: set[str] = set()
    if len(proposal.topics) > topic_budget(settings):
        codes.add("too_many_topics")
    if not set(groups) <= {GROUP[t.competency] for t in proposal.topics}:
        codes.add("missing_group")

    topics: list[PlannedTopic] = []
    seen_topics: set[str] = set()
    seen_questions: set[str] = set()
    for position, item in enumerate(proposal.topics, 1):
        group = GROUP[item.competency]
        if item.competency not in allowed:
            codes.add("competency_not_allowed")
        if len(set(item.fact_refs)) != len(item.fact_refs):
            codes.add("duplicate_fact_ref")
        if not set(item.fact_refs) <= refs.keys():
            codes.add("unknown_fact_ref")  # includes pending/rejected facts: they are never sent
            continue
        cited = list(dict.fromkeys(refs[r] for r in item.fact_refs))
        if group == Q.PROJECT:
            cited_projects = [f for f in cited if f.category == FactCategory.PROJECT]
            if len(cited_projects) != 1:
                codes.add("project_topic_needs_one_project")
            elif not mentions(item.topic, cited_projects[0].fact):
                codes.add("project_not_named")
        if any(not any(mentions(t, f.fact) for t in (item.topic, *item.question_templates))
               for f in cited):
            codes.add("cited_fact_not_mentioned")  # a citation must be real, not decoration
        # The planner's own wording may not name an approved project it doesn't cite (that would
        # present a "generic" topic as being about the candidate), nor a §19 attribute.
        own = [own_words(t, [f.fact for f in cited] + [LABELS[item.competency]])
               for t in (item.topic, *item.question_templates, *item.expected_concepts)]
        # Only a model can write such a reference. The fallback's wording is fixed catalog text
        # whose only candidate text is the project it cites, so a match there is a word that
        # happens to be a project name ("worked in a team" vs a project called "Team").
        if source == PlanSource.AI and any(
                mentions(text, project) for text in own for project in projects):
            codes.add("uncited_project")
        if any(SENSITIVE.search(text) for text in own):
            codes.add("sensitive_attribute")
        if _key(item.topic) in seen_topics:
            codes.add("duplicate_topic")
        seen_topics.add(_key(item.topic))
        for question in item.question_templates:
            if _key(question) in seen_questions:
                codes.add("duplicate_question")
            seen_questions.add(_key(question))
        concepts = list(FOCUS[group]) if group in CODE_SET_CONCEPTS else item.expected_concepts
        if group == Q.TECHNICAL and not concepts:
            codes.add("missing_expected_concepts")
        topics.append(PlannedTopic(
            position=position,
            competency=item.competency,
            question_type=group,
            difficulty=settings.difficulty,  # the candidate's choice; adapting it is Phase 7
            basis=TopicBasis.CANDIDATE_FACT if cited else TopicBasis.GENERIC,
            topic=item.topic,
            question_templates=item.question_templates,
            expected_concepts=concepts,
            facts=cited,
        ))
    if codes:
        raise PlanRejected(codes)
    return InterviewPlan(
        source=source,
        rules_reason=rules_reason,
        settings=settings,
        competencies=list(dict.fromkeys(t.competency for t in topics)),
        omitted_groups=omitted,
        topics=topics,
    )


def fallback_plan(
    settings: PlanSettings, facts: list[FactSnapshot], reason: RulesReason
) -> InterviewPlan:
    """Deterministic plan from the catalog and approved projects only. Validated like any other."""
    groups, _ = plan_groups(settings, facts)
    ref_of = {f.fact_id: ref for ref, f in fact_refs(facts).items()}
    # Same normalisation as the duplicate-topic rule: "TrustLens" and "TrustLens." are one project.
    unique_projects = {_key(f.fact): f for f in reversed(facts)
                       if f.category == FactCategory.PROJECT}
    projects = sorted(unique_projects.values(), key=facts.index)
    role = ROLE_LABELS[settings.target_role]
    queues: dict[QuestionType, list[TopicProposal]] = {
        Q.TECHNICAL: [
            TopicProposal(competency=c, topic=LABELS[c], fact_refs=[],
                          question_templates=[TECHNICAL_QUESTIONS[c]],
                          expected_concepts=list(FOCUS[Q.TECHNICAL]))
            for c in allowed_competencies(settings, [Q.TECHNICAL])
        ],
        Q.PROJECT: [
            TopicProposal(competency=C.PROJECT_UNDERSTANDING, topic=f"Project: {p.fact}",
                          fact_refs=[ref_of[p.fact_id]],
                          question_templates=[q.format(project=p.fact) for q in PROJECT_QUESTIONS],
                          expected_concepts=[])
            for p in projects
        ],
        Q.BEHAVIORAL: [
            TopicProposal(competency=C.BEHAVIORAL, topic=topic, fact_refs=[],
                          question_templates=[question], expected_concepts=[])
            for topic, question in BEHAVIORAL_TOPICS
        ],
        Q.HR: [TopicProposal(competency=C.HR, topic=HR_TOPIC[0], fact_refs=[],
                             question_templates=[HR_TOPIC[1].format(role=role)],
                             expected_concepts=[])],
    }
    # Share the budget round-robin so every group gets a topic, then keep the groups in order.
    counts = dict.fromkeys(groups, 0)
    budget = topic_budget(settings)
    while sum(counts.values()) < budget:
        open_groups = [g for g in groups if counts[g] < len(queues[g])]
        if not open_groups:
            break
        for g in open_groups[: budget - sum(counts.values())]:
            counts[g] += 1
    topics = [t for g in groups for t in queues[g][: counts[g]]]
    return build_plan(PlanProposal(topics=topics), settings, facts,
                      source=PlanSource.RULES, rules_reason=reason)


# ---------- persistence ----------


@dataclass(frozen=True)
class PlanningInput:
    session_id: uuid.UUID
    candidate_id: uuid.UUID
    settings: PlanSettings
    facts: list[FactSnapshot]  # APPROVED only, in ref order
    ai_consent: bool  # when the read transaction ended; save_plan re-reads it under the lock


def approved_facts(db: Session, candidate_id: uuid.UUID) -> list[FactSnapshot]:
    rows = db.execute(
        select(CandidateFact.id, CandidateFact.category, CandidateFact.fact).where(
            CandidateFact.candidate_id == candidate_id,
            CandidateFact.status == FactStatus.APPROVED,
        )
    )
    facts = [FactSnapshot(fact_id=i, category=c, fact=f) for i, c, f in rows]
    facts.sort(key=lambda f: (CATEGORY_ORDER.index(f.category), f.fact.casefold(), f.fact_id))
    return facts[:MAX_PLAN_FACTS]


def prepare_planning(db: Session, session_id: uuid.UUID, settings: PlanSettings) -> PlanningInput:
    """Checks that need no model, then ends the read transaction before any model call."""
    session = db.get(InterviewSession, session_id, populate_existing=True)
    if session is None:
        raise SessionNotFound(session_id)
    if session.status != InterviewStatus.INTERVIEW_PLANNING:
        raise PlanningNotAllowed(session.status)
    facts = approved_facts(db, session.candidate_id)
    plan_groups(settings, facts)  # e.g. project deep dive without a project: ask, call no model
    result = PlanningInput(session.id, session.candidate_id, settings, facts, session.ai_consent)
    db.commit()  # releases the connection: none is held while a model runs
    return result


def save_plan(
    db: Session, inputs: PlanningInput, plan: InterviewPlan, records: list[CallRecord]
) -> tuple[InterviewSession, InterviewPlan]:
    """Store the plan with PLAN_READY under the row lock, re-checking everything that may have
    changed during the model call, consent included. Returns the plan actually stored. The caller
    commits."""
    calls = [ProviderCall.from_record(r) for r in records]
    try:
        db.add_all(calls)
        db.flush()
        session = apply_event(db, inputs.session_id, SessionEvent.PLAN_READY,
                              plan=plan.model_dump(mode="json"))
        if plan.source == PlanSource.AI and not session.ai_consent:
            # Withdrawn while the model ran: its output is discarded, never stored (D2b).
            plan = fallback_plan(inputs.settings, inputs.facts, RulesReason.CONSENT_WITHDRAWN)
            session.plan = plan.model_dump(mode="json")
            db.flush()
        require_cited_facts_unchanged(db, session.candidate_id, plan)
        if plan.source == PlanSource.AI:
            session.plan_provider_call_id = next(c.id for c in reversed(calls) if c.succeeded)
            db.flush()
    except (SessionNotFound, InvalidTransition, PlanStale) as exc:
        db.rollback()  # releases the lock; no part of the plan is kept
        logger.info("Interview plan for session %s not saved (%s)",
                    inputs.session_id, type(exc).__name__)
        if records:  # the calls happened (and cost): keep their metadata on its own
            db.add_all(ProviderCall.from_record(r) for r in records)
            db.commit()
        if isinstance(exc, InvalidTransition):
            raise PlanningNotAllowed(exc.status) from None
        raise
    logger.info("Interview session %s planned: source=%s reason=%s topics=%d",
                session.id, plan.source, plan.rules_reason, len(plan.topics))
    return session, plan


def require_cited_facts_unchanged(
    db: Session, candidate_id: uuid.UUID, plan: InterviewPlan
) -> None:
    cited = {f.fact_id: f for topic in plan.topics for f in topic.facts}
    if not cited:
        return
    current = {
        i: FactSnapshot(fact_id=i, category=c, fact=f)
        for i, c, f in db.execute(
            select(CandidateFact.id, CandidateFact.category, CandidateFact.fact).where(
                CandidateFact.id.in_(cited),
                CandidateFact.candidate_id == candidate_id,
                CandidateFact.status == FactStatus.APPROVED,
            )
        )
    }
    if any(current.get(i) != f for i, f in cited.items()):
        raise PlanStale()

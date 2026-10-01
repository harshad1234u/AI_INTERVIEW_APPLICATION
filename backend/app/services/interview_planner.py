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

ROLE_LABELS = {TargetRole.SOFTWARE_DEVELOPER_INTERN: "Software Developer Intern"}
# get_role_template() / get_competencies(): PRD §8's competencies for the role, plus HR (§42 Mixed).
ROLE_COMPETENCIES = {TargetRole.SOFTWARE_DEVELOPER_INTERN: tuple(C)}
GROUP = {
    C.PROGRAMMING_FUNDAMENTALS: Q.TECHNICAL, C.DATA_STRUCTURES: Q.TECHNICAL, C.DATABASE: Q.TECHNICAL,
    C.WEB_DEVELOPMENT: Q.TECHNICAL, C.PROJECT_UNDERSTANDING: Q.PROJECT, C.BEHAVIORAL: Q.BEHAVIORAL,
    C.HR: Q.HR,
}
LABELS = {
    C.PROGRAMMING_FUNDAMENTALS: "Programming Fundamentals", C.DATA_STRUCTURES: "Data Structures",
    C.DATABASE: "Database", C.WEB_DEVELOPMENT: "Web Development",
    C.PROJECT_UNDERSTANDING: "Project Understanding", C.BEHAVIORAL: "Behavioral", C.HR: "HR",
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
TECHNICAL_QUESTION = "Explain a core concept in {area} and give an example of where it is used."
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
                          question_templates=[TECHNICAL_QUESTION.format(area=LABELS[c].lower())],
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

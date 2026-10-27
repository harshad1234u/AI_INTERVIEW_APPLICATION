"""Planner rules: catalog, validation, grounding, safety and the deterministic fallback. Pure: no DB."""

import itertools
import string
import uuid

import pytest

from app.models.resume import FactCategory as FC
from app.schemas.interview_plan import (
    Competency as C,
    Difficulty,
    ExperienceLevel,
    FactSnapshot,
    InterviewMode as M,
    PlanProposal,
    PlanSettings,
    PlanSource,
    QuestionType as Q,
    RulesReason,
    TargetRole,
    TopicBasis,
)
from app.services.interview_planner import (
    BEHAVIORAL_TOPICS,
    FOCUS,
    GROUP,
    HR_TOPIC,
    LABELS,
    MODE_GROUPS,
    PROJECT_QUESTIONS,
    TECHNICAL_QUESTIONS,
    PlanRejected,
    ProjectRequired,
    build_plan,
    fact_refs,
    fallback_plan,
    plan_groups,
    topic_budget,
)


def fact(category: FC, text: str) -> FactSnapshot:
    return FactSnapshot(fact_id=uuid.uuid4(), category=category, fact=text)


TRUSTLENS = fact(FC.PROJECT, "TrustLens")
CAMPUS = fact(FC.PROJECT, "Campus Connect")
PYTHON = fact(FC.SKILL, "Python")
REACT = fact(FC.SKILL, "React")
INTERN = fact(FC.EXPERIENCE, "Software Engineering Intern | Acme Corp")
FACTS = [TRUSTLENS, CAMPUS, PYTHON, REACT, INTERN]  # refs F1..F5 in this order
NO_PROJECTS = [PYTHON, REACT, INTERN]


def settings(mode: M = M.MIXED, duration: int = 15, **kw: object) -> PlanSettings:
    return PlanSettings(target_role=kw.get("role", TargetRole.SOFTWARE_DEVELOPER_INTERN),
                        experience_level=kw.get("level", ExperienceLevel.STUDENT), mode=mode,
                        difficulty=kw.get("difficulty", Difficulty.MEDIUM),
                        duration_minutes=duration)


def topic(competency: C, title: str, refs: list[str] | None = None, questions: list[str] | None = None,
          concepts: list[str] | None = None) -> dict:
    return {"competency": competency, "topic": title, "fact_refs": refs or [],
            "question_templates": questions or [f"Tell me about {title}."],
            "expected_concepts": ["indexes"] if concepts is None else concepts}


VALID_MIXED = [
    topic(C.DATABASE, "Database indexing", questions=["How does an index speed up a query?"]),
    topic(C.WEB_DEVELOPMENT, "React state", ["F4"], ["How do you manage state in React?"]),
    topic(C.PROJECT_UNDERSTANDING, "TrustLens architecture", ["F1"],
          ["Explain the architecture of TrustLens.", "Why did you choose its tech stack?"]),
    topic(C.BEHAVIORAL, "Teamwork", questions=["Describe a time you worked in a team."]),
    topic(C.HR, "Motivation", questions=["Why this internship?"], concepts=[]),
]


def build(topics: list[dict], s: PlanSettings | None = None, facts=FACTS):
    return build_plan(PlanProposal(topics=topics), s or settings(), facts, source=PlanSource.AI)


def rejected(topics: list[dict], s: PlanSettings | None = None, facts=FACTS) -> frozenset[str]:
    with pytest.raises(PlanRejected) as exc:
        build(topics, s, facts)
    return exc.value.codes


# ---------- catalog ----------


@pytest.mark.parametrize(("duration", "budget"), [(15, 5), (30, 10), (45, 15)])
def test_topic_budget(duration: int, budget: int) -> None:
    assert topic_budget(settings(duration=duration)) == budget


def test_mode_groups_follow_prd_42() -> None:
    assert MODE_GROUPS[M.MIXED] == (Q.TECHNICAL, Q.PROJECT, Q.BEHAVIORAL, Q.HR)
    assert plan_groups(settings(M.MIXED), FACTS) == ([Q.TECHNICAL, Q.PROJECT, Q.BEHAVIORAL, Q.HR], [])


def test_mixed_without_a_project_omits_the_group_openly() -> None:
    assert plan_groups(settings(M.MIXED), NO_PROJECTS) == (
        [Q.TECHNICAL, Q.BEHAVIORAL, Q.HR], [Q.PROJECT])


def test_project_deep_dive_requires_an_approved_project() -> None:
    with pytest.raises(ProjectRequired):
        plan_groups(settings(M.PROJECT_DEEP_DIVE), NO_PROJECTS)


def test_settings_are_closed_sets() -> None:
    for bad in ({"duration_minutes": 20}, {"difficulty": "EXPERT"}, {"mode": "HIRING"},
                {"target_role": "CTO"}, {"experience_level": "SENIOR"}):
        with pytest.raises(ValueError):
            PlanSettings(**{**settings().model_dump(), **bad})


# ---------- deterministic fallback: every supported combination ----------

COMBOS = list(itertools.product(TargetRole, M, Difficulty, (15, 30, 45),
                                ("no_facts", "no_projects", "facts")))


@pytest.mark.parametrize(("role", "mode", "difficulty", "duration", "profile"), COMBOS,
                         ids=lambda x: str(x))
def test_fallback_is_valid_for_every_combination(role, mode, difficulty, duration, profile) -> None:
    facts = {"no_facts": [], "no_projects": NO_PROJECTS, "facts": FACTS}[profile]
    s = settings(mode, duration, role=role, difficulty=difficulty)
    if mode == M.PROJECT_DEEP_DIVE and profile != "facts":
        with pytest.raises(ProjectRequired):
            fallback_plan(s, facts, RulesReason.NOT_REQUESTED)
        return
    plan = fallback_plan(s, facts, RulesReason.NOT_REQUESTED)  # already passed build_plan
    groups, omitted = plan_groups(s, facts)
    assert (plan.source, plan.rules_reason, plan.omitted_groups) == (
        PlanSource.RULES, RulesReason.NOT_REQUESTED, omitted)
    assert 1 <= len(plan.topics) <= topic_budget(s)
    assert {t.question_type for t in plan.topics} == set(groups)  # every required group, no other
    assert [t.position for t in plan.topics] == list(range(1, len(plan.topics) + 1))
    for t in plan.topics:
        assert t.difficulty == difficulty and t.question_type == GROUP[t.competency]
        if t.basis == TopicBasis.GENERIC:
            assert t.facts == []
        else:  # only approved project facts, and the fallback never cites anything else
            assert [f.category for f in t.facts] == [FC.PROJECT] and t.facts[0] in facts
            assert t.facts[0].fact in t.topic


def test_fallback_uses_each_approved_project_once_and_invents_none() -> None:
    duplicate = fact(FC.PROJECT, "trustlens")  # same project from a second resume
    plan = fallback_plan(settings(M.PROJECT_DEEP_DIVE, 45), [TRUSTLENS, duplicate, CAMPUS],
                         RulesReason.PROVIDERS_FAILED)
    assert [t.topic for t in plan.topics] == ["Project: TrustLens", "Project: Campus Connect"]
    assert all(t.expected_concepts == list(FOCUS[Q.PROJECT]) for t in plan.topics)


def test_fallback_mixed_shares_the_budget_across_groups() -> None:
    plan = fallback_plan(settings(M.MIXED, 15), FACTS, RulesReason.NOT_REQUESTED)
    assert [t.question_type for t in plan.topics] == [
        Q.TECHNICAL, Q.TECHNICAL, Q.PROJECT, Q.BEHAVIORAL, Q.HR]


# Approved project names that are ordinary words in the fallback's own wording ("worked in a
# team", "give an example", "Software Developer Intern role"). These used to fail validation and
# made planning a 500 for that candidate.
CATALOG_WORDS = ["Team", "Example", "Core", "Concepts", "In", "You", "What", "Role", "Time",
                 "Learning", "Decisions", "Motivation", "Intern", "Software"]


@pytest.mark.parametrize("duration", (15, 30, 45))
@pytest.mark.parametrize("mode", list(M))
@pytest.mark.parametrize("name", CATALOG_WORDS)
def test_fallback_survives_project_names_that_are_catalog_words(name, mode, duration) -> None:
    project = fact(FC.PROJECT, name)
    plan = fallback_plan(settings(mode, duration), [project, PYTHON], RulesReason.NOT_REQUESTED)
    for t in plan.topics:
        if t.question_type == Q.PROJECT:
            assert (t.basis, t.facts) == (TopicBasis.CANDIDATE_FACT, [project])
        else:  # generic wording that merely contains the word is still generic
            assert (t.basis, t.facts) == (TopicBasis.GENERIC, [])


def test_fallback_survives_a_project_named_project() -> None:
    named = fact(FC.PROJECT, "Project")
    plan = fallback_plan(settings(M.PROJECT_DEEP_DIVE, 15), [named, TRUSTLENS],
                         RulesReason.NOT_REQUESTED)
    assert [(t.topic, t.facts) for t in plan.topics] == [
        ("Project: Project", [named]), ("Project: TrustLens", [TRUSTLENS])]


def test_fallback_treats_names_differing_only_in_case_spacing_or_end_punctuation_as_one() -> None:
    variants = [fact(FC.PROJECT, n) for n in ("TrustLens.", "trustlens !", " TRUSTLENS")]
    plan = fallback_plan(settings(M.PROJECT_DEEP_DIVE, 45), [TRUSTLENS, *variants, CAMPUS],
                         RulesReason.NOT_REQUESTED)
    assert [t.topic for t in plan.topics] == ["Project: TrustLens", "Project: Campus Connect"]


def test_catalog_wording_takes_no_candidate_text_except_the_cited_project() -> None:
    """Why only AI proposals are checked for uncited projects: fallback text is these constants,
    filled with a label, the role and the one project the topic cites."""
    texts = (*TECHNICAL_QUESTIONS.values(), *PROJECT_QUESTIONS,
             *itertools.chain(*BEHAVIORAL_TOPICS), *HR_TOPIC)
    fields = {f for text in texts for _, f, _, _ in string.Formatter().parse(text) if f}
    assert fields == {"project", "role"}


def test_every_technical_area_has_its_own_curated_question() -> None:
    assert set(TECHNICAL_QUESTIONS) == {c for c, g in GROUP.items() if g == Q.TECHNICAL}
    plan = fallback_plan(settings(M.TECHNICAL, 15), FACTS, RulesReason.NOT_REQUESTED)
    assert [(t.topic, t.question_templates) for t in plan.topics] == [
        (label, [TECHNICAL_QUESTIONS[c]]) for c, label in (
            (C.PROGRAMMING_FUNDAMENTALS, "Programming Fundamentals"),
            (C.DATA_STRUCTURES, "Data Structures"), (C.DATABASE, "Database"),
            (C.WEB_DEVELOPMENT, "Web Development"))]
    assert all(t.expected_concepts == list(FOCUS[Q.TECHNICAL]) for t in plan.topics)


def _catalog(project: str = "TrustLens") -> dict[str, str]:
    from app.services.interviewer import GENERIC_FOLLOW_UP

    return {**{c.value: q for c, q in TECHNICAL_QUESTIONS.items()},
            **{f"project {i}": q.format(project=project) for i, q in enumerate(PROJECT_QUESTIONS)},
            **dict(BEHAVIORAL_TOPICS), "hr": HR_TOPIC[1].format(role="Software Developer Intern"),
            "generic follow-up": GENERIC_FOLLOW_UP}


@pytest.mark.parametrize("project", ["TrustLens", "Campus Connect", "Example", "Core", "Team"])
def test_no_two_fallback_questions_are_duplicates(project: str) -> None:
    """Every fallback question can be asked: none is a §33 duplicate of another (Decision B).
    The rule itself is unchanged; the catalog was reworded."""
    from app.services.interviewer import DUPLICATE_RATIO, REPHRASE_TEMPLATE, is_duplicate

    assert DUPLICATE_RATIO == 0.85
    texts = _catalog(project)
    for (a, x), (b, y) in itertools.combinations(texts.items(), 2):
        assert not is_duplicate(x, y), (a, b)
    # A framed rephrase of one topic's question never hides another topic's question either.
    titles = {c.value: LABELS[c] for c in TECHNICAL_QUESTIONS}
    for (a, x), (b, y) in itertools.permutations(texts.items(), 2):
        framed = REPHRASE_TEMPLATE.format(topic=titles.get(a, a), question=x)
        assert not is_duplicate(y, framed), (a, b)


def test_data_structures_and_database_are_distinct_but_the_old_frame_was_not() -> None:
    from app.services.interviewer import is_duplicate

    assert not is_duplicate(TECHNICAL_QUESTIONS[C.DATA_STRUCTURES], TECHNICAL_QUESTIONS[C.DATABASE])
    # The old shared frame is still caught: the duplicate rule was not weakened.
    old = "Explain a core concept in {area} and give an example of where it is used."
    assert is_duplicate(old.format(area="data structures"), old.format(area="database"))


def test_ai_proposals_still_may_not_name_an_uncited_project() -> None:
    team = fact(FC.PROJECT, "Team")
    topics = [
        topic(C.DATABASE, "Database indexing", questions=["How does an index speed up a query?"]),
        topic(C.PROJECT_UNDERSTANDING, "Team architecture", ["F1"],
              ["Explain the architecture of Team."]),
        topic(C.BEHAVIORAL, "Teamwork", questions=["Describe a time you worked in a team."]),
        topic(C.HR, "Motivation", questions=["Why this internship?"], concepts=[]),
    ]
    assert "uncited_project" in rejected(topics, facts=[team])


# ---------- validation of proposals ----------


def test_valid_proposal_builds_the_stored_plan() -> None:
    plan = build(VALID_MIXED)
    assert plan.source == PlanSource.AI and plan.rules_reason is None and plan.omitted_groups == []
    assert plan.competencies == [C.DATABASE, C.WEB_DEVELOPMENT, C.PROJECT_UNDERSTANDING,
                                 C.BEHAVIORAL, C.HR]
    db, web, project, behavioral, hr = plan.topics
    assert (db.basis, db.facts) == (TopicBasis.GENERIC, [])
    assert (web.basis, web.facts) == (TopicBasis.CANDIDATE_FACT, [REACT])
    assert (project.basis, project.facts) == (TopicBasis.CANDIDATE_FACT, [TRUSTLENS])
    assert all(t.difficulty == Difficulty.MEDIUM for t in plan.topics)


def test_project_and_behavioral_concepts_are_set_by_code_not_the_model() -> None:
    topics = [dict(t) for t in VALID_MIXED]
    topics[2]["expected_concepts"] = ["uses ONNX", "detects phishing with 99% accuracy"]
    topics[3]["expected_concepts"] = ["is a natural leader"]
    plan = build(topics)
    assert plan.topics[2].expected_concepts == list(FOCUS[Q.PROJECT])
    assert plan.topics[3].expected_concepts == list(FOCUS[Q.BEHAVIORAL])
    assert plan.topics[0].expected_concepts == ["indexes"]  # technical: domain concepts kept


def replace(index: int, **changes: object) -> list[dict]:
    topics = [dict(t) for t in VALID_MIXED]
    topics[index] = {**topics[index], **changes}
    return topics


@pytest.mark.parametrize(
    ("topics", "code"),
    [
        (VALID_MIXED + [topic(C.DATA_STRUCTURES, "Hash maps")], "too_many_topics"),
        (VALID_MIXED[:4], "missing_group"),  # MIXED without HR
        (replace(0, fact_refs=["F9"]), "unknown_fact_ref"),
        (replace(1, fact_refs=["F4", "F4"]), "duplicate_fact_ref"),
        # project topics: exactly one approved PROJECT, named in the topic
        (replace(2, fact_refs=[]), "project_topic_needs_one_project"),
        (replace(2, fact_refs=["F3"], topic="Python project",
                 question_templates=["How did you use Python?"]),
         "project_topic_needs_one_project"),
        (replace(2, fact_refs=["F1", "F2"], topic="TrustLens and Campus Connect"),
         "project_topic_needs_one_project"),
        (replace(2, topic="Architecture deep dive"), "project_not_named"),
        # citations must be real, generic topics must not be about the candidate
        (replace(1, question_templates=["How does a virtual DOM work?"], topic="Virtual DOM"),
         "cited_fact_not_mentioned"),
        (replace(0, question_templates=["How did TrustLens store its data?"]), "uncited_project"),
        (replace(3, question_templates=["Tell me about teamwork on Campus Connect."]),
         "uncited_project"),
        (replace(0, expected_concepts=["TrustLens schema"]), "uncited_project"),
        # §19 attributes and duplicates
        (replace(4, question_templates=["What is your religion?"]), "sensitive_attribute"),
        (replace(3, question_templates=["Does your gender affect teamwork?"]),
         "sensitive_attribute"),
        (replace(4, topic="database  INDEXING."), "duplicate_topic"),
        (replace(4, question_templates=["how does an index speed up a query"]),
         "duplicate_question"),
        (replace(0, expected_concepts=[]), "missing_expected_concepts"),
    ],
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_rule_violations_are_rejected(topics: list[dict], code: str) -> None:
    assert code in rejected(topics)


def test_competency_outside_the_mode_is_rejected() -> None:
    technical = settings(M.TECHNICAL)
    assert "competency_not_allowed" in rejected(
        [topic(C.DATABASE, "Indexes"), topic(C.BEHAVIORAL, "Teamwork")], technical)


def test_pending_or_rejected_facts_cannot_be_cited() -> None:
    """Refs exist only for the facts supplied, and only APPROVED facts are ever supplied."""
    only_python = [PYTHON]
    assert fact_refs(only_python) == {"F1": PYTHON}
    assert "unknown_fact_ref" in rejected(
        [topic(C.PROGRAMMING_FUNDAMENTALS, "Python", ["F2"], ["Explain Python generators."])],
        settings(M.TECHNICAL), only_python)


def test_mixed_without_projects_rejects_a_project_topic_and_accepts_the_rest() -> None:
    no_project_mixed = [t for t in VALID_MIXED if t["competency"] != C.PROJECT_UNDERSTANDING]
    no_project_mixed[1] = topic(C.WEB_DEVELOPMENT, "Web basics", questions=["What is HTTP?"])
    plan = build(no_project_mixed, facts=[PYTHON])
    assert plan.omitted_groups == [Q.PROJECT]
    invented = no_project_mixed + [topic(C.PROJECT_UNDERSTANDING, "Your chatbot project")]
    assert {"competency_not_allowed", "project_topic_needs_one_project"} <= rejected(
        invented, facts=[PYTHON])


def test_symbol_names_and_the_candidates_own_words_are_handled() -> None:
    cpp, forum = fact(FC.SKILL, "C++"), fact(FC.PROJECT, "Religion Q&A Forum")
    facts = [forum, cpp]  # F1, F2
    topics = [
        topic(C.PROGRAMMING_FUNDAMENTALS, "C++ memory", ["F2"], ["How does C++ manage memory?"]),
        topic(C.PROJECT_UNDERSTANDING, "Religion Q&A Forum design", ["F1"],
              ["Explain the architecture of Religion Q&A Forum."]),
        topic(C.BEHAVIORAL, "Teamwork", questions=["Describe a time you worked in a team."]),
        topic(C.HR, "Motivation", questions=["Why this internship?"], concepts=[]),
    ]
    plan = build(topics, facts=facts)
    assert plan.topics[0].facts == [cpp] and plan.topics[1].facts == [forum]
    # A §19 word inside the candidate's own approved project name is theirs; in the planner's
    # own wording it is rejected.
    asks = topic(C.HR, "Motivation", questions=["What is your religion?"], concepts=[])
    assert "sensitive_attribute" in rejected([*topics[:3], asks], facts=facts)

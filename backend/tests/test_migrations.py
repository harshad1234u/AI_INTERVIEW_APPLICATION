import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.gateway import ErrorKind, ModelCapability
from app.db.session import engine
from app.models import Candidate
from app.models.interview_session import PRE_PLAN_STATUSES, InterviewStatus

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _current_heads() -> set[str]:
    with engine.connect() as conn:
        return set(MigrationContext.configure(conn).get_current_heads())


def test_downgrade_upgrade_roundtrip_and_models_in_sync() -> None:
    cfg = Config(str(ALEMBIC_INI))
    command.downgrade(cfg, "base")
    tables = set(inspect(engine).get_table_names())
    assert not tables & {"candidates", "resumes", "candidate_facts", "interview_sessions"}

    command.upgrade(cfg, "head")
    # Fails if SQLAlchemy models have changes with no matching migration.
    command.check(cfg)
    assert _current_heads() == set(ScriptDirectory.from_config(cfg).get_heads())


def test_candidates_table_schema() -> None:
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("candidates")}
    assert set(cols) == {"id", "email", "name", "created_at"}
    assert not any(c["nullable"] for c in cols.values())
    assert insp.get_pk_constraint("candidates")["constrained_columns"] == ["id"]
    uniques = {u["name"]: u["column_names"] for u in insp.get_unique_constraints("candidates")}
    assert uniques == {"uq_candidates_email": ["email"]}
    checks = {c["name"] for c in insp.get_check_constraints("candidates")}
    assert checks == {"ck_candidates_email_lowercase", "ck_candidates_name_not_blank"}


def test_interview_sessions_table_schema() -> None:
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("interview_sessions")}
    # Lifecycle (Phase 5) + the validated plan (Phase 6). No answers or other personal data.
    assert set(cols) == {"id", "candidate_id", "status", "created_at", "updated_at", "plan",
                         "plan_provider_call_id"}
    assert [n for n, c in cols.items() if c["nullable"]] == ["plan", "plan_provider_call_id"]
    assert {c["name"] for c in insp.get_check_constraints("interview_sessions")} == {
        "ck_interview_sessions_status", "ck_interview_sessions_plan_matches_status",
        "ck_interview_sessions_plan_is_object",
    }
    fks = {fk["referred_table"]: (fk["constrained_columns"], fk["options"].get("ondelete"))
           for fk in insp.get_foreign_keys("interview_sessions")}
    assert fks == {"candidates": (["candidate_id"], "CASCADE"),
                   "provider_calls": (["plan_provider_call_id"], "SET NULL")}
    indexes = {i["name"]: i for i in insp.get_indexes("interview_sessions")}
    active = indexes["uq_interview_sessions_one_active_per_candidate"]
    assert active["unique"] and active["column_names"] == ["candidate_id"]
    assert "COMPLETED" in active["dialect_options"]["postgresql_where"]
    assert not indexes["ix_interview_sessions_candidate_id"]["unique"]


def test_interview_sessions_migration_downgrades_alone() -> None:
    """The Phase 5 revision only adds interview_sessions; stepping back leaves the rest intact."""
    cfg = Config(str(ALEMBIC_INI))
    before = {t: {c["name"] for c in inspect(engine).get_check_constraints(t)}
              for t in ("candidates", "resumes", "candidate_facts", "provider_calls")}
    command.downgrade(cfg, "a41f0c9e7b25")  # through the Phase 6 revision as well
    try:
        insp = inspect(engine)
        assert "interview_sessions" not in insp.get_table_names()
        assert {t: {c["name"] for c in insp.get_check_constraints(t)} for t in before} == before
    finally:
        command.upgrade(cfg, "head")
    assert "interview_sessions" in inspect(engine).get_table_names()


def test_database_generates_id_and_created_at(db_session: Session) -> None:
    c = Candidate(email="gen@example.com", name="Gen")
    db_session.add(c)
    db_session.flush()
    assert c.id is not None
    assert c.created_at is not None and c.created_at.tzinfo is not None


@pytest.mark.parametrize(
    ("row", "constraint"),
    [
        ({"email": "a@example.com", "name": None}, None),
        ({"email": None, "name": "A"}, None),
        ({"email": "A@Example.com", "name": "A"}, "ck_candidates_email_lowercase"),
        ({"email": "a@example.com", "name": "   "}, "ck_candidates_name_not_blank"),
    ],
    ids=["null-name", "null-email", "uppercase-email", "blank-name"],
)
def test_database_rejects_invalid_rows(
    db_session: Session, row: dict, constraint: str | None
) -> None:
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(insert(Candidate).values(**row))
    if constraint:
        assert exc.value.orig.diag.constraint_name == constraint


def test_database_enforces_unique_email(db_session: Session) -> None:
    db_session.execute(insert(Candidate).values(email="u@example.com", name="A"))
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(insert(Candidate).values(email="u@example.com", name="B"))
    assert exc.value.orig.diag.constraint_name == "uq_candidates_email"


# ---------- resumes / candidate_facts ----------


def test_resume_tables_schema() -> None:
    insp = inspect(engine)
    assert {c["name"] for c in insp.get_columns("resumes")} == {
        "id", "candidate_id", "raw_text", "parsed_json", "upload_status", "created_at"
    }
    assert {c["name"] for c in insp.get_columns("candidate_facts")} == {
        "id", "candidate_id", "resume_id", "category", "fact", "extracted_fact", "source",
        "source_section", "source_text", "status", "extracted_by", "provider_call_id", "created_at",
    }
    fks = {
        fk["name"]: (fk["constrained_columns"], fk["referred_table"], fk["options"].get("ondelete"))
        for table in ("resumes", "candidate_facts")
        for fk in insp.get_foreign_keys(table)
    }
    assert fks == {
        "fk_resumes_candidate_id_candidates": (["candidate_id"], "candidates", "CASCADE"),
        "fk_candidate_facts_candidate_id_candidates": (["candidate_id"], "candidates", "CASCADE"),
        "fk_candidate_facts_resume_id_resumes": (["resume_id", "candidate_id"], "resumes", "CASCADE"),
        "fk_candidate_facts_provider_call_id_provider_calls": (
            ["provider_call_id"], "provider_calls", "SET NULL"
        ),
    }
    assert {c["name"] for c in insp.get_check_constraints("resumes")} == {"ck_resumes_upload_status"}
    assert {c["name"] for c in insp.get_check_constraints("candidate_facts")} == {
        "ck_candidate_facts_category", "ck_candidate_facts_source", "ck_candidate_facts_status",
        "ck_candidate_facts_fact_not_blank", "ck_candidate_facts_extracted_fact_not_blank",
        "ck_candidate_facts_extracted_by",
    }


def test_provider_calls_schema_holds_no_content_columns() -> None:
    insp = inspect(engine)
    assert {c["name"] for c in insp.get_columns("provider_calls")} == {
        "id", "request_id", "capability", "requested_provider", "provider", "model", "succeeded",
        "attempts", "fallback_used", "error_type", "latency_ms", "input_tokens", "output_tokens",
        "total_tokens", "provider_request_id", "created_at",
    }
    assert insp.get_foreign_keys("provider_calls") == []  # no link to a candidate
    assert {c["name"] for c in insp.get_check_constraints("provider_calls")} == {
        "ck_provider_calls_capability", "ck_provider_calls_error_type"
    }


def test_database_accepts_every_error_kind_and_nothing_else(db_session: Session) -> None:
    # The CHECK constraint is hand-written in migrations: keep it in step with ErrorKind.
    insert_call = text(
        "INSERT INTO provider_calls (request_id, capability, requested_provider, succeeded, "
        "attempts, fallback_used, error_type, latency_ms) "
        "VALUES ('r', 'PROFILE_EXTRACTION', 'groq', false, 1, false, :e, 0)"
    )
    for kind in ErrorKind:
        db_session.execute(insert_call, {"e": kind.value})
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(insert_call, {"e": "QUOTA_GUESS"})
    assert exc.value.orig.diag.constraint_name == "ck_provider_calls_error_type"


def test_existing_facts_default_to_rule_extraction(db_session: Session) -> None:
    c = _candidate(db_session)
    fact_id = _fact(db_session, c, _resume(db_session, c))
    row = db_session.execute(
        text("SELECT extracted_by, provider_call_id FROM candidate_facts WHERE id = :i"), {"i": fact_id}
    ).one()
    assert tuple(row) == ("RULES", None)
    with pytest.raises(IntegrityError) as exc:
        _fact(db_session, c, _resume(db_session, c), extracted_by="LLM_SELF_APPROVED")
    assert exc.value.orig.diag.constraint_name == "ck_candidate_facts_extracted_by"


def _candidate(db: Session, email: str = "c@example.com") -> str:
    return str(db.scalar(insert(Candidate).values(email=email, name="C").returning(Candidate.id)))


def _resume(db: Session, candidate_id: str, status: str = "PROCESSED") -> str:
    return str(db.scalar(text(
        "INSERT INTO resumes (candidate_id, parsed_json, upload_status) "
        "VALUES (:c, '{}', :s) RETURNING id"
    ), {"c": candidate_id, "s": status}))


def _fact(db: Session, candidate_id: str, resume_id: str, **overrides: str) -> str:
    row = {"category": "SKILL", "fact": "Python", "extracted_fact": "Python", "source": "RESUME",
           "source_section": "Skills", "source_text": "Python", **overrides}
    cols = ", ".join(row)
    return str(db.scalar(text(
        f"INSERT INTO candidate_facts (candidate_id, resume_id, {cols}) "
        f"VALUES (:candidate_id, :resume_id, {', '.join(':' + k for k in row)}) RETURNING id"
    ), {"candidate_id": candidate_id, "resume_id": resume_id, **row}))


def test_fact_defaults_to_pending_review(db_session: Session) -> None:
    c = _candidate(db_session)
    fact_id = _fact(db_session, c, _resume(db_session, c))
    status = db_session.scalar(text("SELECT status FROM candidate_facts WHERE id = :i"), {"i": fact_id})
    assert status == "PENDING_REVIEW"


@pytest.mark.parametrize(
    ("bad", "constraint"),
    [
        ({"status": "TRUSTED"}, "ck_candidate_facts_status"),
        ({"category": "PERSONALITY"}, "ck_candidate_facts_category"),
        ({"source": "AI_INFERENCE"}, "ck_candidate_facts_source"),
        ({"fact": "  "}, "ck_candidate_facts_fact_not_blank"),
        ({"extracted_fact": ""}, "ck_candidate_facts_extracted_fact_not_blank"),
    ],
    ids=["status", "category", "source", "blank-fact", "blank-extracted"],
)
def test_database_rejects_invalid_facts(db_session: Session, bad: dict, constraint: str) -> None:
    c = _candidate(db_session)
    r = _resume(db_session, c)
    with pytest.raises(IntegrityError) as exc:
        _fact(db_session, c, r, **bad)
    assert exc.value.orig.diag.constraint_name == constraint


def test_database_rejects_invalid_resumes(db_session: Session) -> None:
    c = _candidate(db_session)
    with pytest.raises(IntegrityError) as exc, db_session.begin_nested():
        _resume(db_session, c, status="DONE")
    assert exc.value.orig.diag.constraint_name == "ck_resumes_upload_status"
    with pytest.raises(IntegrityError) as exc:
        _resume(db_session, str(uuid.uuid4()))
    assert exc.value.orig.diag.constraint_name == "fk_resumes_candidate_id_candidates"


def test_fact_cannot_point_at_another_candidates_resume(db_session: Session) -> None:
    alice, bob = _candidate(db_session, "a@example.com"), _candidate(db_session, "b@example.com")
    bobs_resume = _resume(db_session, bob)
    with pytest.raises(IntegrityError) as exc:
        _fact(db_session, alice, bobs_resume)
    assert exc.value.orig.diag.constraint_name == "fk_candidate_facts_resume_id_resumes"


def test_deleting_candidate_cascades_in_the_database(db_session: Session) -> None:
    c = _candidate(db_session)
    _fact(db_session, c, _resume(db_session, c))
    db_session.execute(text("DELETE FROM candidates WHERE id = :c"), {"c": c})
    for table in ("resumes", "candidate_facts"):
        left = db_session.scalar(text(f"SELECT count(*) FROM {table} WHERE candidate_id = :c"), {"c": c})
        assert left == 0


# ---------- Phase 6: interview plan ----------

PLAN_REVISION, BEFORE_PLAN_REVISION = "b8d14f2a9c63", "e5813b741341"
CALL_COLUMNS = ("INSERT INTO provider_calls (request_id, capability, requested_provider, "
                "succeeded, attempts, fallback_used, latency_ms) ")


def _session(db: Session, status: str, plan: str | None) -> None:
    """Raw insert, one candidate each (so the one-active-session index never interferes)."""
    with db.begin_nested():
        db.execute(text(
            "INSERT INTO interview_sessions (candidate_id, status, plan) "
            "VALUES (:c, :s, CAST(:p AS jsonb))"
        ), {"c": _candidate(db, f"{uuid.uuid4().hex}@example.com"), "s": status, "p": plan})


@pytest.mark.parametrize("status", [s.value for s in InterviewStatus])
def test_plan_exists_exactly_when_the_session_is_past_planning(
    db_session: Session, status: str
) -> None:
    """Every lifecycle state, against PostgreSQL itself: READY and every later state (PAUSED and
    COMPLETED included) must have a plan; CREATED..INTERVIEW_PLANNING must not."""
    past_planning = status not in {s.value for s in PRE_PLAN_STATUSES}
    _session(db_session, status, '{"version": 1}' if past_planning else None)  # legitimate
    with pytest.raises(IntegrityError) as exc:
        _session(db_session, status, None if past_planning else '{"version": 1}')
    assert exc.value.orig.diag.constraint_name == "ck_interview_sessions_plan_matches_status"


@pytest.mark.parametrize("plan", ["[]", '"plan"', "null", "1"])
def test_plan_must_be_a_json_object(db_session: Session, plan: str) -> None:
    with pytest.raises(IntegrityError) as exc:
        _session(db_session, "READY", plan)
    assert exc.value.orig.diag.constraint_name == "ck_interview_sessions_plan_is_object"


def test_status_and_plan_updates_are_checked_too(db_session: Session) -> None:
    sid = db_session.scalar(text(
        "INSERT INTO interview_sessions (candidate_id, status) VALUES (:c, 'INTERVIEW_PLANNING') "
        "RETURNING id"), {"c": _candidate(db_session)})
    update = text("UPDATE interview_sessions SET status = :s, plan = CAST(:p AS jsonb) WHERE id = :i")
    for status, plan in [("READY", None), ("INTERVIEW_PLANNING", "{}")]:  # half a planning step
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(update, {"s": status, "p": plan, "i": sid})
    db_session.execute(update, {"s": "READY", "p": "{}", "i": sid})  # both together: fine
    for status in ("ASKING", "WAITING_FOR_ANSWER", "PAUSED", "REPORT_GENERATION", "COMPLETED"):
        db_session.execute(update, {"s": status, "p": "{}", "i": sid})  # later steps keep it
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text("UPDATE interview_sessions SET plan = NULL WHERE id = :i"),
                           {"i": sid})


def test_database_accepts_every_capability_and_nothing_else(db_session: Session) -> None:
    insert_call = text(CALL_COLUMNS + "VALUES ('r', :c, 'groq', true, 1, false, 0)")
    for capability in ModelCapability:
        db_session.execute(insert_call, {"c": capability.value})
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(insert_call, {"c": "SELF_APPROVAL"})
    assert exc.value.orig.diag.constraint_name == "ck_provider_calls_capability"


def test_deleting_call_metadata_keeps_the_plan(db_session: Session) -> None:
    call = db_session.scalar(text(
        CALL_COLUMNS + "VALUES ('r', 'INTERVIEW_PLANNING', 'groq', true, 1, false, 0) RETURNING id"))
    sid = db_session.scalar(text(
        "INSERT INTO interview_sessions (candidate_id, status, plan, plan_provider_call_id) "
        "VALUES (:c, 'READY', '{}', :p) RETURNING id"), {"c": _candidate(db_session), "p": call})
    db_session.execute(text("DELETE FROM provider_calls WHERE id = :p"), {"p": call})
    row = db_session.execute(text(
        "SELECT plan, plan_provider_call_id FROM interview_sessions WHERE id = :i"), {"i": sid}).one()
    assert tuple(row) == ({}, None)


@pytest.fixture
def committed_planned_session() -> Iterator[None]:
    """A READY session with a plan, committed for real (not rolled back); cleaned up after."""
    with engine.begin() as conn:
        cid = conn.scalar(insert(Candidate).values(
            email=f"{uuid.uuid4().hex}@example.com", name="Downgrade").returning(Candidate.id))
        conn.execute(text("INSERT INTO interview_sessions (candidate_id, status, plan) "
                          "VALUES (:c, 'READY', CAST(:p AS jsonb))"),
                     {"c": cid, "p": '{"version": 1}'})
    try:
        yield
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM candidates WHERE id = :c"), {"c": cid})


def test_downgrade_refuses_while_plans_exist(committed_planned_session: None) -> None:
    cfg = Config(str(ALEMBIC_INI))
    with pytest.raises(RuntimeError, match="Refusing to downgrade: 1 interview session"):
        command.downgrade(cfg, BEFORE_PLAN_REVISION)
    # Nothing changed: still at head, and the plan is still there.
    assert _current_heads() == {PLAN_REVISION}
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM interview_sessions WHERE plan IS NOT NULL"))


def test_plan_revision_downgrades_and_re_upgrades_cleanly() -> None:
    cfg = Config(str(ALEMBIC_INI))
    with engine.begin() as conn:  # planning-call metadata, which the old CHECK can't hold
        conn.execute(text(CALL_COLUMNS + "VALUES ('roundtrip-test', 'INTERVIEW_PLANNING', "
                                         "'groq', false, 1, false, 0)"))
    command.downgrade(cfg, BEFORE_PLAN_REVISION)
    try:
        insp = inspect(engine)
        assert {c["name"] for c in insp.get_columns("interview_sessions")} == {
            "id", "candidate_id", "status", "created_at", "updated_at"}
        with engine.connect() as conn:
            assert not conn.scalar(text(
                "SELECT count(*) FROM provider_calls WHERE request_id = 'roundtrip-test'"))
    finally:
        command.upgrade(cfg, "head")
    command.check(cfg)
    assert _current_heads() == {PLAN_REVISION}

"""Manual profile facts (Phase 13, docs/phase-13-manual-profile-plan.md).

A candidate can type in their own skills, projects, experience, education and certifications.
Typing a fact is its confirmation (PRD §18 level 1), so it is APPROVED from the start and reaches
the planner and interviewer exactly like an approved resume fact: they read facts by candidate
and status only. No model is involved.

Transaction contract (as elsewhere): every write locks the candidate row first, so the cap and
the duplicate check cannot race. The caller commits.
"""

import uuid

from sqlalchemy import func, null, select
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateFact
from app.models.resume import MANUAL_FACTS_MAX, FactCategory, FactSource, FactStatus

DUPLICATE = "This fact is already in your profile."
TOO_MANY = f"You can add at most {MANUAL_FACTS_MAX} facts of your own. Delete one to add another."


class ManualFactConflict(Exception):
    """409. The message names the reason, never the fact."""


def _lock_candidate(db: Session, candidate_id: uuid.UUID) -> None:
    db.execute(select(Candidate.id).where(Candidate.id == candidate_id).with_for_update())


def _check_not_duplicate(db: Session, candidate_id: uuid.UUID, category: FactCategory, text: str,
                         exclude: uuid.UUID | None = None) -> None:
    """Exact duplicates only (M4): same category and text ignoring case, among the candidate's
    manual facts and resume facts that are not rejected. Text is already whitespace-normalized
    by the shared FactText rule, the same one resume-fact edits use."""
    query = select(CandidateFact.id).where(
        CandidateFact.candidate_id == candidate_id,
        CandidateFact.category == category,
        func.lower(CandidateFact.fact) == func.lower(text),
        CandidateFact.status != FactStatus.REJECTED,
    )
    if exclude is not None:
        query = query.where(CandidateFact.id != exclude)
    if db.scalar(query.limit(1)) is not None:
        raise ManualFactConflict(DUPLICATE)


def add_manual_fact(db: Session, candidate_id: uuid.UUID, category: FactCategory,
                    text: str) -> CandidateFact:
    _lock_candidate(db, candidate_id)
    count = db.scalar(select(func.count()).select_from(CandidateFact).where(
        CandidateFact.candidate_id == candidate_id, CandidateFact.source == FactSource.MANUAL))
    if count >= MANUAL_FACTS_MAX:
        raise ManualFactConflict(TOO_MANY)
    _check_not_duplicate(db, candidate_id, category, text)
    fact = CandidateFact(
        candidate_id=candidate_id, category=category, fact=text,
        extracted_fact=text,  # the text as first entered, kept for audit like an extraction
        source=FactSource.MANUAL, status=FactStatus.APPROVED,
        # No resume provenance at all (the database CHECK requires exactly this).
        # null(), not None: None would let extracted_by fall back to its server default (RULES).
        resume_id=None, source_section=None, source_text=None, extracted_by=null(),
    )
    db.add(fact)
    db.flush()
    return fact


def edit_manual_fact(db: Session, fact: CandidateFact, text: str) -> CandidateFact:
    """In place: same id, category and status; extracted_fact keeps the original text. A plan
    citing the old text sees the change through the interviewer's D8 check."""
    _lock_candidate(db, fact.candidate_id)
    _check_not_duplicate(db, fact.candidate_id, fact.category, text, exclude=fact.id)
    fact.fact = text
    db.flush()
    return fact

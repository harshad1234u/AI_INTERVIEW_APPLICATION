"""Manual profile facts (Phase 13): the signed-in candidate's own skills, projects and so on."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import current_candidate
from app.api.routes.candidates import get_candidate
from app.db.session import get_db
from app.models import Candidate, CandidateFact
from app.models.resume import MANUAL_FACT_UNIQUE_INDEX, FactSource
from app.schemas.resume import FactResponse, ManualFactCreate, ManualFactUpdate
from app.services.manual_facts import (
    DUPLICATE,
    ManualFactConflict,
    add_manual_fact,
    edit_manual_fact,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["manual facts"])

NOT_FOUND = "Fact not found"


def get_manual_fact(
    fact_id: uuid.UUID,
    current: Candidate = Depends(current_candidate),
    db: Session = Depends(get_db),
) -> CandidateFact:
    """A manual fact of the signed-in candidate. Anyone else's fact, and any resume fact, is a
    404 exactly like a missing one (A4): resume facts are reviewed through their resume."""
    fact = db.get(CandidateFact, fact_id)
    if fact is None or fact.candidate_id != current.id or fact.source != FactSource.MANUAL:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return fact


def _write(db: Session, write):
    """Runs the service write and commits. Conflicts are 409; fact text is never logged."""
    try:
        result = write()
        db.commit()
        return result
    except ManualFactConflict as exc:
        db.rollback()  # nothing was written; this releases the candidate row lock
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except OperationalError:
        db.rollback()
        raise  # the app turns this into a 503
    except SQLAlchemyError as exc:
        db.rollback()
        constraint = getattr(getattr(getattr(exc, "orig", None), "diag", None),
                             "constraint_name", None)
        if isinstance(exc, IntegrityError) and constraint == MANUAL_FACT_UNIQUE_INDEX:
            # Backstop only: the row lock already serialises duplicate checks.
            raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None
        logger.error("Manual fact write failed (%s, constraint %s)", type(exc).__name__,
                     constraint)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Could not save fact") from None


@router.get("/candidates/{candidate_id}/manual-facts", response_model=list[FactResponse])
def list_manual_facts(
    candidate: Candidate = Depends(get_candidate), db: Session = Depends(get_db)
) -> list[CandidateFact]:
    # Same order as a resume's facts: extracted_fact never changes, so an edit keeps its place.
    return list(db.scalars(
        select(CandidateFact)
        .where(CandidateFact.candidate_id == candidate.id,
               CandidateFact.source == FactSource.MANUAL)
        .order_by(CandidateFact.category, func.lower(CandidateFact.extracted_fact),
                  CandidateFact.id)
    ))


@router.post("/candidates/{candidate_id}/manual-facts", response_model=FactResponse,
             status_code=status.HTTP_201_CREATED)
def create_manual_fact(
    body: ManualFactCreate,
    candidate: Candidate = Depends(get_candidate),
    db: Session = Depends(get_db),
) -> CandidateFact:
    """Approved at once: typing it is the candidate's confirmation (M1)."""
    fact = _write(db, lambda: add_manual_fact(db, candidate.id, body.category, body.fact))
    logger.info("Candidate %s added manual fact %s", candidate.id, fact.id)
    return fact


@router.patch("/manual-facts/{fact_id}", response_model=FactResponse)
def update_manual_fact(
    body: ManualFactUpdate,
    fact: CandidateFact = Depends(get_manual_fact),
    db: Session = Depends(get_db),
) -> CandidateFact:
    return _write(db, lambda: edit_manual_fact(db, fact, body.fact))


@router.delete("/manual-facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manual_fact(
    fact: CandidateFact = Depends(get_manual_fact), db: Session = Depends(get_db)
) -> None:
    db.delete(fact)
    _write(db, lambda: None)

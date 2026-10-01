import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Candidate
from app.models.candidate import EMAIL_UNIQUE_CONSTRAINT
from app.schemas.candidate import CandidateCreate, CandidateResponse, CandidateUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/candidates", tags=["candidates"])


def get_candidate(candidate_id: uuid.UUID, db: Session = Depends(get_db)) -> Candidate:
    # Single access point for a candidate by id: the ownership check goes here once auth exists.
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return candidate


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == EMAIL_UNIQUE_CONSTRAINT:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "A candidate with this email already exists"
            ) from None
        # The DB error text contains row values (personal data); log only the constraint.
        logger.error("Candidate write violated constraint %s", constraint)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not save candidate"
        ) from None


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(body: CandidateCreate, db: Session = Depends(get_db)) -> Candidate:
    candidate = Candidate(**body.model_dump())
    db.add(candidate)
    _commit(db)
    return candidate


@router.get("/{candidate_id}", response_model=CandidateResponse)
def read_candidate(candidate: Candidate = Depends(get_candidate)) -> Candidate:
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    body: CandidateUpdate,
    candidate: Candidate = Depends(get_candidate),
    db: Session = Depends(get_db),
) -> Candidate:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    _commit(db)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate: Candidate = Depends(get_candidate), db: Session = Depends(get_db)
) -> None:
    # Later phases add child tables with ON DELETE CASCADE so this removes all candidate data.
    db.delete(candidate)
    _commit(db)

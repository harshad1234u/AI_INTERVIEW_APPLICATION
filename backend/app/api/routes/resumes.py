import logging
import uuid
from typing import Annotated

import anyio.from_thread
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.gateway import ModelGateway, ModelUnavailableError
from app.ai.profile_agent import extract_profile
from app.ai.providers import get_model_gateway
from app.api.deps import current_candidate
from app.api.routes.candidates import get_candidate
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Candidate, CandidateFact, ProviderCall, Resume
from app.models.resume import Extractor, FactSource, ResumeStatus
from app.schemas.resume import AIExtractionResponse, FactResponse, FactUpdate, ResumeResponse
from app.services.resume_extractor import process_pdf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["resumes"])

NOT_PDF = "Only PDF resumes are supported."


def too_large_detail(settings: Settings) -> str:
    return f"The file is too large. The maximum resume size is {settings.max_resume_size_mb} MB."


def get_resume(
    resume_id: uuid.UUID,
    current: Candidate = Depends(current_candidate),
    db: Session = Depends(get_db),
) -> Resume:
    """Single access point for a resume by id. Another candidate's resume is a 404, exactly like
    one that does not exist (A4)."""
    resume = db.get(Resume, resume_id)
    if resume is None or resume.candidate_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return resume


def _commit(db: Session) -> None:
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        raise  # the app turns this into a 503
    except SQLAlchemyError as exc:
        db.rollback()
        # DB error text includes the SQL parameters, i.e. resume content: log class + constraint only.
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        logger.error(
            "Resume write failed (%s, constraint %s)",
            type(exc).__name__,
            getattr(diag, "constraint_name", None),
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not save resume"
        ) from None


def _read_pdf(file: UploadFile, settings: Settings) -> bytes:
    """Validate the upload and return its bytes. The client's filename is checked, never used."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, NOT_PDF)
    if (file.content_type or "").split(";")[0].strip().lower() != "application/pdf":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, NOT_PDF)
    data = file.file.read(settings.max_resume_bytes + 1)
    if len(data) > settings.max_resume_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, too_large_detail(settings))
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The file is empty.")
    # Content, not the name, decides: a renamed image or text file fails here.
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "The file is not a valid PDF.")
    return data


@router.post("/resumes", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: Annotated[UploadFile, File()],
    candidate: Candidate = Depends(current_candidate),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ResumeResponse:
    """For the signed-in candidate. The form carries only the file: a client-supplied candidate
    id is never trusted."""
    result = process_pdf(_read_pdf(file, settings))
    # Resume and facts are written in one transaction with the final status: never half-processed.
    resume = Resume(
        candidate_id=candidate.id,
        upload_status=result.status,
        raw_text=result.raw_text,
        parsed_json=result.parsed_json,
    )
    resume.facts = [
        CandidateFact(
            category=f.category,
            fact=f.fact,
            extracted_fact=f.fact,
            source=FactSource.RESUME,
            source_section=f.section,
            source_text=f.source_text,
        )
        for f in result.facts
    ]
    db.add(resume)
    _commit(db)
    logger.info(
        "Resume %s stored: %s, %d facts pending review",
        resume.id, resume.upload_status, len(result.facts),
    )
    return ResumeResponse.from_model(resume)


@router.get("/candidates/{candidate_id}/resumes", response_model=list[ResumeResponse])
def list_candidate_resumes(
    candidate: Candidate = Depends(get_candidate), db: Session = Depends(get_db)
) -> list[ResumeResponse]:
    resumes = db.scalars(
        select(Resume)
        .where(Resume.candidate_id == candidate.id)
        .order_by(Resume.created_at.desc(), Resume.id)
    )
    return [ResumeResponse.from_model(r) for r in resumes]


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
def read_resume(resume: Resume = Depends(get_resume)) -> ResumeResponse:
    return ResumeResponse.from_model(resume)


@router.get("/resumes/{resume_id}/facts", response_model=list[FactResponse])
def list_facts(
    resume: Resume = Depends(get_resume), db: Session = Depends(get_db)
) -> list[CandidateFact]:
    return list(
        db.scalars(
            select(CandidateFact)
            .where(CandidateFact.resume_id == resume.id)
            # extracted_fact never changes, so a fact keeps its place after an edit.
            .order_by(
                CandidateFact.category, func.lower(CandidateFact.extracted_fact), CandidateFact.id
            )
        )
    )


@router.patch("/resumes/{resume_id}/facts/{fact_id}", response_model=FactResponse)
def review_fact(
    fact_id: uuid.UUID,
    body: FactUpdate,
    resume: Resume = Depends(get_resume),
    db: Session = Depends(get_db),
) -> CandidateFact:
    fact = db.get(CandidateFact, fact_id)
    if fact is None or fact.resume_id != resume.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fact not found")
    # Only the candidate's explicit edit/decision changes a fact; source and extracted_fact stay.
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(fact, field, value)
    _commit(db)
    return fact


@router.post("/resumes/{resume_id}/ai-extraction", response_model=AIExtractionResponse)
def run_ai_extraction(
    resume: Resume = Depends(get_resume),
    db: Session = Depends(get_db),
    gateway: ModelGateway | None = Depends(get_model_gateway),
) -> AIExtractionResponse:
    """Opt-in, per resume: the candidate's click is the consent to send the text to a provider.

    Adds grounded AI facts as PENDING_REVIEW beside the rule-based ones. On any AI failure the
    resume and its existing facts are left exactly as they were.
    """
    if gateway is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "AI extraction is not configured on this server.")
    if resume.upload_status != ResumeStatus.PROCESSED or not resume.raw_text:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Only resumes that were read successfully can use AI extraction.")
    raw_text = resume.raw_text
    db.commit()  # end the read transaction: hold no DB connection during the model call

    try:
        # Sync route (sync DB session) calling the async gateway on the event loop.
        result = anyio.from_thread.run(extract_profile, gateway, raw_text)
    except ModelUnavailableError as exc:
        db.add(ProviderCall.from_record(exc.record))
        _commit(db)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI extraction is unavailable right now. Your resume and its facts are unchanged.",
        ) from None

    call = ProviderCall.from_record(result.record)
    db.add(call)
    db.flush()
    existing = {tuple(row) for row in db.execute(
        select(CandidateFact.category, func.lower(CandidateFact.extracted_fact))
        .where(CandidateFact.resume_id == resume.id)
    )}
    new = [f for f in result.facts if (f.category, f.fact.lower()) not in existing]
    db.add_all(
        CandidateFact(
            candidate_id=resume.candidate_id,
            resume_id=resume.id,
            category=f.category,
            fact=f.fact,
            extracted_fact=f.fact,
            source=FactSource.RESUME,
            source_section=f.section,
            source_text=f.source_text,
            extracted_by=Extractor.AI,
            provider_call_id=call.id,
            # status is deliberately never set here: the DB default is PENDING_REVIEW.
        )
        for f in new
    )
    _commit(db)
    record = result.record
    return AIExtractionResponse(
        request_id=record.request_id,
        requested_provider=record.requested_provider,
        provider=record.provider,
        model=record.model,
        fallback_used=record.fallback_used,
        attempts=record.attempts,
        latency_ms=record.latency_ms,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        total_tokens=record.total_tokens,
        facts_added=len(new),
        facts_already_listed=len(result.facts) - len(new),
        facts_rejected=sum(result.rejected.values()),
    )


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume: Resume = Depends(get_resume), db: Session = Depends(get_db)) -> None:
    db.delete(resume)  # its facts go with it (ON DELETE CASCADE), approved ones included
    _commit(db)

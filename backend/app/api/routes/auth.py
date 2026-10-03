"""Email + password authentication with server-side sessions (Phase 12).

The raw session token only ever travels in the HttpOnly cookie; the database holds its SHA-256.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    SESSION_COOKIE,
    clear_session_cookie,
    current_candidate,
    set_session_cookie,
)
from app.api.routes.candidates import candidate_write
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Candidate
from app.schemas.candidate import CandidateResponse, LoginRequest, RegisterRequest
from app.services.limits import LOGIN, REGISTER, Limit, LimitReached, consume, network_key
from app.services.auth import (
    AccountLocked,
    InvalidCredentials,
    authenticate,
    end_session,
    new_candidate,
    start_session,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

BAD_CREDENTIALS = "Email or password is incorrect."
LOCKED = "Too many failed attempts. Please try again in 15 minutes."
THROTTLED = {
    REGISTER.scope: "Too many accounts were created from your network. Please try again in "
                    "{minutes} minutes.",
    LOGIN.scope: "Too many sign-in attempts from your network. Please try again in {minutes} "
                 "minutes.",
}


def _throttle(db: Session, request: Request, limit: Limit) -> None:
    """Per network, before any password is hashed or any account is looked up: the answer is the
    same whether or not the email exists. Committed at once, so a refused login still counts."""
    try:
        consume(db, limit, network_key(request.client.host if request.client else None))
    except LimitReached as exc:
        db.rollback()
        minutes = max(1, -(-exc.retry_after // 60))
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            THROTTLED[limit.scope].format(minutes=minutes),
                            headers={"Retry-After": str(exc.retry_after)}) from None
    db.commit()


@router.post("/register", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Candidate:
    """Creates the candidate and signs them in. A duplicate email is a 409 (enumeration through
    registration is accepted until email verification exists)."""
    _throttle(db, request, REGISTER)
    with candidate_write(db):
        candidate = new_candidate(db, body.email, body.name, body.password)
        token = start_session(db, candidate.id)
    set_session_cookie(response, token, settings)
    logger.info("Candidate %s registered", candidate.id)
    return candidate


@router.post("/login", response_model=CandidateResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Candidate:
    _throttle(db, request, LOGIN)
    try:
        candidate = authenticate(db, body.email, body.password)
    except InvalidCredentials:
        db.commit()  # keeps the failure count (and any new lock)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_CREDENTIALS) from None
    except AccountLocked:
        db.rollback()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, LOCKED) from None
    token = start_session(db, candidate.id)
    db.commit()
    set_session_cookie(response, token, settings)
    return candidate


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Deletes the server-side session. Idempotent: without a valid session it just clears the
    cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        end_session(db, token)
        db.commit()
    clear_session_cookie(response, settings)


@router.get("/me", response_model=CandidateResponse)
def me(candidate: Candidate = Depends(current_candidate)) -> Candidate:
    return candidate

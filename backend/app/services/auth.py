"""Registration, login with lockout, and server-side sessions. No model is ever involved."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_HASH,
    hash_password,
    new_session_token,
    token_hash,
    verify_password,
)
from app.models import AuthSession, Candidate

SESSION_TTL = timedelta(days=7)  # absolute: a session is never extended
MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)


class InvalidCredentials(Exception):
    """Unknown email, no password set, or wrong password: deliberately indistinguishable."""


class AccountLocked(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def new_candidate(db: Session, email: str, name: str, password: str) -> Candidate:
    """Adds the candidate (the caller commits; a duplicate email fails on the unique constraint)."""
    candidate = Candidate(email=email, name=name, password_hash=hash_password(password))
    db.add(candidate)
    db.flush()
    return candidate


def authenticate(db: Session, email: str, password: str) -> Candidate:
    """The candidate whose password matches. The caller commits on success AND on
    InvalidCredentials, so the failure count is kept.

    The candidate row is locked (FOR UPDATE) for the whole check, so parallel attempts are
    counted one at a time and cannot get past the threshold.
    """
    candidate = db.scalars(
        select(Candidate).where(Candidate.email == email).with_for_update()
    ).one_or_none()
    if candidate is None or candidate.password_hash is None:
        verify_password(password, DUMMY_HASH)  # same cost as a wrong password
        raise InvalidCredentials
    now = _now()
    if candidate.locked_until is not None and candidate.locked_until > now:
        raise AccountLocked
    if not verify_password(password, candidate.password_hash):
        candidate.failed_logins += 1
        if candidate.failed_logins >= MAX_FAILED_LOGINS:
            candidate.failed_logins = 0
            candidate.locked_until = now + LOCKOUT
        raise InvalidCredentials
    candidate.failed_logins = 0
    candidate.locked_until = None
    return candidate


def start_session(db: Session, candidate_id: uuid.UUID) -> str:
    """Stores a new session and returns its raw token, which is never stored."""
    now = _now()
    # Housekeeping: this candidate's expired sessions are useless; drop them while here.
    db.execute(delete(AuthSession).where(AuthSession.candidate_id == candidate_id,
                                         AuthSession.expires_at <= now))
    token = new_session_token()
    db.add(AuthSession(token_hash=token_hash(token), candidate_id=candidate_id,
                       created_at=now, expires_at=now + SESSION_TTL))
    db.flush()
    return token


def session_candidate(db: Session, token: str) -> Candidate | None:
    """The candidate signed in with this token, or None if it is unknown, revoked or expired."""
    return db.scalars(
        select(Candidate).join(AuthSession, AuthSession.candidate_id == Candidate.id)
        .where(AuthSession.token_hash == token_hash(token), AuthSession.expires_at > _now())
    ).one_or_none()


def end_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))

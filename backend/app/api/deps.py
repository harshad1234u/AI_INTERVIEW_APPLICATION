"""Request dependencies shared by the routers."""

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.models import Candidate
from app.services.auth import SESSION_TTL, session_candidate

SESSION_COOKIE = "coach_session"
NOT_AUTHENTICATED = "Please log in."


def current_candidate(request: Request, db: Session = Depends(get_db)) -> Candidate:
    """The signed-in candidate, from the HttpOnly session cookie: the only source of identity
    for every protected route. No cookie, or an unknown, revoked or expired session, is a 401."""
    token = request.cookies.get(SESSION_COOKIE)
    candidate = session_candidate(db, token) if token else None
    if candidate is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_AUTHENTICATED)
    return candidate


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    # HttpOnly: page JavaScript can never read the token. Lax: not sent on cross-site POSTs.
    response.set_cookie(SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()),
                        path="/", httponly=True, samesite="lax",
                        secure=settings.auth_cookie_secure)


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=settings.auth_cookie_secure)

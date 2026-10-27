import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.routes import auth, candidates, health, interview_sessions, manual_facts, resumes
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Room for multipart boundaries and part headers around the file.
MULTIPART_OVERHEAD_BYTES = 64 * 1024
# Every other request is JSON; the largest real one (a 10,000-character answer) is ~40 KB.
JSON_MAX_BYTES = 256 * 1024
TOO_LARGE = "The request is too large."
UPLOAD_PATH = "/api/resumes"


class BodySizeLimit:
    """Stops reading a request body once it passes max_bytes.

    Starlette spools a whole upload to disk before the endpoint runs, so the endpoint's own size
    check alone would still accept unlimited bytes. Counting as bytes arrive also covers chunked
    requests that send no Content-Length.
    """

    def __init__(self, app: ASGIApp, max_bytes: int, detail: str, *,
                 upload_path: str | None = None, upload_max_bytes: int = 0,
                 upload_detail: str = "") -> None:
        self.app, self.max_bytes, self.detail = app, max_bytes, detail
        # The resume upload alone may be larger (and gets its own message).
        self.upload_path, self.upload_max_bytes = upload_path, upload_max_bytes
        self.upload_detail = upload_detail

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0
        upload = self.upload_path is not None and scope.get("path") == self.upload_path
        limit = self.upload_max_bytes if upload else self.max_bytes
        detail = self.upload_detail if upload else self.detail

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > limit:
                # Raised inside body parsing, so FastAPI returns it as a normal 413 response.
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail)
            return message

        await self.app(scope, limited_receive, send)


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class OriginCheck:
    """CSRF defence for cookie authentication (A5, with SameSite=Lax): a state-changing request
    must come from an allowed origin. A missing Origin is refused too: browsers send one on every
    POST, PUT, PATCH and DELETE, so only non-browser clients omit it, and they can add it."""

    def __init__(self, app: ASGIApp, allowed: list[str]) -> None:
        self.app, self.allowed = app, frozenset(allowed)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (scope["type"] == "http" and scope["method"] not in SAFE_METHODS
                and Headers(scope=scope).get("origin") not in self.allowed):
            response = JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                                    content={"detail": "Request origin not allowed."})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI echoes the rejected input; on auth routes that can be a password. Drop it there.
    if not request.url.path.startswith("/api/auth/"):
        return await request_validation_exception_handler(request, exc)
    errors = [{k: v for k, v in e.items() if k != "input"} for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        content={"detail": jsonable_encoder(errors)})


async def database_unavailable(_: Request, exc: Exception) -> JSONResponse:
    # Log the driver error class only: its message can include host/user details.
    orig = getattr(exc, "orig", None)
    logger.error("Database unavailable (%s)", type(orig or exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Service temporarily unavailable. Please try again."},
    )


def configure_logging(level: str) -> None:
    """Uvicorn configures only its own loggers, so without this the app's INFO lines (model
    calls, validation failures, transitions: metadata only, PRD §64) would never be written."""
    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
    app_logger.setLevel(level)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    is_prod = settings.environment == "production"
    app = FastAPI(
        title="AI Interview Coach API",
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    # Added before CORS, so CORS wraps it: preflights never reach the Origin check.
    app.add_middleware(OriginCheck, allowed=settings.cors_origin_list)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,  # the session cookie
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_middleware(
        BodySizeLimit,
        max_bytes=JSON_MAX_BYTES,
        detail=TOO_LARGE,
        upload_path=UPLOAD_PATH,
        upload_max_bytes=settings.max_resume_bytes + MULTIPART_OVERHEAD_BYTES,
        upload_detail=resumes.too_large_detail(settings),
    )
    app.add_exception_handler(OperationalError, database_unavailable)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.include_router(health.router, prefix="/api")
    # A7: production still serves the health check only; enabling the app there is a later phase.
    if not is_prod:
        app.include_router(auth.router, prefix="/api")
        app.include_router(candidates.router, prefix="/api")
        app.include_router(resumes.router, prefix="/api")
        app.include_router(manual_facts.router, prefix="/api")
        app.include_router(interview_sessions.router, prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port)

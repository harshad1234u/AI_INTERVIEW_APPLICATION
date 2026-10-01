import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.routes import candidates, health, interview_sessions, resumes
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Room for multipart boundaries, part headers and the candidate_id field around the file.
MULTIPART_OVERHEAD_BYTES = 64 * 1024


class BodySizeLimit:
    """Stops reading a request body once it passes max_bytes.

    Starlette spools a whole upload to disk before the endpoint runs, so the endpoint's own size
    check alone would still accept unlimited bytes. Counting as bytes arrive also covers chunked
    requests that send no Content-Length.
    """

    def __init__(self, app: ASGIApp, max_bytes: int, detail: str) -> None:
        self.app, self.max_bytes, self.detail = app, max_bytes, detail

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                # Raised inside body parsing, so FastAPI returns it as a normal 413 response.
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, self.detail)
            return message

        await self.app(scope, limited_receive, send)


async def database_unavailable(_: Request, exc: Exception) -> JSONResponse:
    # Log the driver error class only: its message can include host/user details.
    orig = getattr(exc, "orig", None)
    logger.error("Database unavailable (%s)", type(orig or exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Service temporarily unavailable. Please try again."},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    is_prod = settings.environment == "production"
    app = FastAPI(
        title="AI Interview Coach API",
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_middleware(
        BodySizeLimit,
        max_bytes=settings.max_resume_bytes + MULTIPART_OVERHEAD_BYTES,
        detail=resumes.too_large_detail(settings),
    )
    app.add_exception_handler(OperationalError, database_unavailable)
    app.include_router(health.router, prefix="/api")
    # Candidate, resume and session routes have no authentication yet: never serve them in production.
    if not is_prod:
        app.include_router(candidates.router, prefix="/api")
        app.include_router(resumes.router, prefix="/api")
        app.include_router(interview_sessions.router, prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port)

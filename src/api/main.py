"""
FastAPI application factory for AI Meeting Assistant.

Entry point: uvicorn src.api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    analysis,
    exports,
    jira,
    meetings,
    reviews,
    settings,
    transcriptions,
)
from src.config import get_logger, get_settings
from src.db.session import get_engine, init_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB engine on startup, dispose on shutdown."""
    app_settings = get_settings()
    if not app_settings.postgres_url:
        logger.warning("POSTGRES_URL not set - database endpoints will fail.")
    else:
        try:
            init_engine()
            logger.info("PostgreSQL engine initialized successfully.")
        except Exception as exc:
            logger.error(f"Failed to connect to PostgreSQL: {exc}")
    yield
    try:
        engine = get_engine()
        await engine.dispose()
        logger.info("PostgreSQL engine disposed.")
    except RuntimeError:
        pass


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware if enabled."""
    app_settings = get_settings()

    if not app_settings.rate_limit_enabled:
        logger.info("Rate limiting is disabled.")
        return

    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info(
            f"Rate limiting enabled: default={app_settings.rate_limit_default}"
        )
    except ImportError:
        logger.warning(
            "slowapi not installed - rate limiting disabled. "
            "Install with: pip install slowapi"
        )


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware from settings."""
    app_settings = get_settings()

    origins = app_settings.get_cors_origins()
    methods = app_settings.get_cors_methods()
    headers = app_settings.get_cors_headers()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=app_settings.cors_allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
    )

    if origins == ["*"]:
        logger.warning(
            "CORS is configured to allow all origins (*). "
            "Consider restricting CORS_ORIGINS in production."
        )
    else:
        logger.info(f"CORS configured for origins: {origins}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Meeting Assistant API",
        version="1.0.0",
        description="RESTful API for AI Meeting Assistant.",
        lifespan=lifespan,
    )

    # Configure middleware
    setup_cors(app)
    setup_rate_limiting(app)

    # Register API routers
    prefix = "/api/v1"
    app.include_router(meetings.router, prefix=prefix)
    app.include_router(transcriptions.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(jira.router, prefix=prefix)
    app.include_router(exports.router, prefix=prefix)
    app.include_router(settings.router, prefix=prefix)

    @app.get("/api/v1/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint for monitoring."""
        db_ok = False
        try:
            from sqlalchemy import text

            from src.db.session import _session_factory

            if _session_factory:
                async with _session_factory() as session:
                    await session.execute(text("SELECT 1"))
                    db_ok = True
        except Exception:
            pass
        return {"status": "ok", "db": "ok" if db_ok else "unavailable"}

    @app.get("/api/v1/jobs/{job_id}", tags=["jobs"])
    async def get_job_status(job_id: str) -> dict:
        """Get Celery task status by job ID."""
        from celery.result import AsyncResult

        from src.workers.celery_app import celery_app

        result = AsyncResult(job_id, app=celery_app)
        response: dict = {"job_id": job_id, "state": result.state}
        if result.state == "SUCCESS":
            response["result"] = result.result
        elif result.state == "FAILURE":
            response["error"] = str(result.info)
        return response

    return app


app = create_app()

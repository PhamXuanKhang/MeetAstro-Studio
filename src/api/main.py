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
    stream,
    transcriptions,
)
from src.config import get_logger, get_settings
from src.db.supabase_client import get_supabase_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Supabase client on startup."""
    app_settings = get_settings()
    if not app_settings.supabase_url or not app_settings.supabase_service_role_key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — "
            "database endpoints will fail."
        )
    else:
        try:
            client = get_supabase_client()
            logger.info(
                "Supabase client initialized: %s",
                app_settings.supabase_url,
            )
            # Verify connection with a simple query
            client.table("meetings").select("id").limit(1).execute()
            logger.info("Supabase connection verified.")
        except Exception as exc:
            logger.error("Failed to connect to Supabase: %s", exc)
    yield
    # Cleanup on shutdown
    try:
        from src.services.stream_session_manager import get_stream_manager
        manager = get_stream_manager()
        await manager.close_all()
    except Exception as exc:
        logger.warning("Error closing streaming sessions on shutdown: %s", exc)


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

    setup_cors(app)
    setup_rate_limiting(app)

    prefix = "/api/v1"
    app.include_router(meetings.router, prefix=prefix)
    app.include_router(transcriptions.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(jira.router, prefix=prefix)
    app.include_router(exports.router, prefix=prefix)
    app.include_router(settings.router, prefix=prefix)
    app.include_router(stream.router, prefix=prefix)

    @app.get("/api/v1/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint for monitoring."""
        supabase_ok = False
        try:
            client = get_supabase_client()
            client.table("meetings").select("id").limit(1).execute()
            supabase_ok = True
        except Exception:
            pass
        return {"status": "ok", "supabase": "ok" if supabase_ok else "unavailable"}

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

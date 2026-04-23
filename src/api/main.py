"""
FastAPI app factory cho AI Meeting Assistant.

Entrypoint: uvicorn src.api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import analysis, exports, jira, meetings, reviews, settings, transcriptions
from src.config import get_logger, get_settings
from src.db.session import get_engine, init_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo DB engine khi app start, dispose khi shutdown."""
    settings = get_settings()
    if not settings.postgres_url:
        logger.warning("POSTGRES_URL chưa được set — các endpoint DB sẽ lỗi.")
    else:
        try:
            init_engine()
            logger.info("PostgreSQL engine đã khởi tạo.")
        except Exception as exc:
            logger.error(f"Không kết nối được PostgreSQL: {exc}")
    yield
    try:
        engine = get_engine()
        await engine.dispose()
    except RuntimeError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Meeting Assistant API",
        version="1.0.0",
        description="RESTful API cho AI Meeting Assistant — transcription, analysis, review, Jira.",
        lifespan=lifespan,
    )

    # CORS cho Flet desktop (localhost) và web
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Đăng ký routers
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
        """Health check endpoint."""
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
        """Trạng thái Celery task theo job_id."""
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

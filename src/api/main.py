"""
FastAPI application factory for AI Meeting Assistant.

Entry point: uvicorn src.api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
import json
import urllib.error
import urllib.request

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

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

API_PREFIX = "/api/v1"
WEB_STATIC_DIR = Path(__file__).resolve().parents[2] / "website" / "dist"
DOWNLOAD_DIR = Path("/app/downloads")
INDEX_CACHE_CONTROL = "no-cache"
ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
EXE_MEDIA_TYPE = "application/vnd.microsoft.portable-executable"
GITHUB_RELEASE_API_TIMEOUT_SECONDS = 5

class CacheStaticFiles(StaticFiles):
    """Serve Vite assets with immutable cache headers."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = ASSET_CACHE_CONTROL
        return response

def get_download_filename() -> str:
    """Return a safe EXE filename configured by environment."""
    filename = get_settings().app_download_filename.strip()
    if not filename or filename != Path(filename).name or not filename.lower().endswith(".exe"):
        raise HTTPException(status_code=404, detail="Windows installer is not published.")
    return filename

def get_download_file_path() -> Path:
    """Resolve the configured EXE path inside the downloads directory."""
    return DOWNLOAD_DIR / get_download_filename()

def get_external_download_url() -> str:
    """Return configured external EXE URL when it is safe to expose."""
    download_url = get_settings().app_download_url.strip()
    parsed = urlparse(download_url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return ""
    if not parsed.path.lower().endswith(".exe"):
        return ""
    return download_url

def format_file_size(size_bytes: int) -> str:
    """Format release asset size for display."""
    if size_bytes <= 0:
        return ""
    size_mb = size_bytes / (1024 * 1024)
    if size_mb >= 10:
        return f"{size_mb:.0f} MB"
    return f"{size_mb:.1f} MB"

def parse_release_version(tag_name: str) -> str:
    """Parse semantic version from release tag."""
    return tag_name[1:] if tag_name.startswith("v") else tag_name

@lru_cache(maxsize=1)
def get_github_release_metadata() -> dict:
    """Fetch latest public GitHub Release metadata for the Windows installer."""
    repo = get_settings().app_download_github_repo.strip()
    if not repo or "/" not in repo:
        return {}
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "MeetAstro"},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=GITHUB_RELEASE_API_TIMEOUT_SECONDS,
        ) as response:
            release = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("GitHub latest release metadata unavailable: %s", exc)
        return {}

    for asset in release.get("assets", []):
        filename = str(asset.get("name", ""))
        download_url = str(asset.get("browser_download_url", ""))
        if filename.startswith("MeetAstro-Setup-") and filename.endswith(".exe") and download_url:
            return {
                "available": True,
                "url": download_url,
                "filename": filename,
                "version": parse_release_version(str(release.get("tag_name", ""))),
                "size": format_file_size(int(asset.get("size") or 0)),
                "platform": "Windows",
                "publishedAt": release.get("published_at") or "",
            }
    return {}

def build_download_metadata() -> dict:
    """Build runtime metadata for the Windows installer."""
    app_settings = get_settings()
    github_metadata = get_github_release_metadata()
    if github_metadata:
        return github_metadata

    filename = app_settings.app_download_filename.strip()
    external_url = get_external_download_url()
    available = bool(external_url)
    url = external_url
    if not available:
        try:
            available = get_download_file_path().is_file()
            url = "/downloads/windows" if available else ""
        except HTTPException:
            available = False
            url = ""
    return {
        "available": available,
        "url": url,
        "filename": filename,
        "version": app_settings.app_download_version.strip(),
        "size": app_settings.app_download_size.strip(),
        "platform": "Windows",
    }

def setup_website_routes(app: FastAPI) -> None:
    """Serve the landing page and download endpoints."""
    assets_dir = WEB_STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", CacheStaticFiles(directory=str(assets_dir)), name="website-assets")

    @app.get("/downloads/metadata.json", include_in_schema=False)
    async def download_metadata() -> JSONResponse:
        return JSONResponse(
            build_download_metadata(),
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/download/windows", include_in_schema=False)
    @app.get("/downloads/windows", include_in_schema=False)
    async def download_windows() -> FileResponse:
        file_path = get_download_file_path()
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="Windows installer is not published.")
        return FileResponse(
            path=str(file_path),
            media_type=EXE_MEDIA_TYPE,
            filename=get_download_filename(),
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_website(path: str, request: Request) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        index_path = WEB_STATIC_DIR / "index.html"
        if not index_path.is_file():
            raise HTTPException(status_code=404, detail="Website build is not available.")
        return FileResponse(
            path=str(index_path),
            media_type="text/html",
            headers={"Cache-Control": INDEX_CACHE_CONTROL},
        )



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

    prefix = API_PREFIX
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

    setup_website_routes(app)

    return app


app = create_app()

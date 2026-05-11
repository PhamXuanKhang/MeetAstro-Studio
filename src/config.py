"""
Centralized configuration and logging setup for AI Meeting Assistant.

Uses pydantic-settings BaseSettings with lru_cache for validation and caching.
All configuration is loaded from environment variables and .env file.
"""
import logging
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    """Application configuration loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── OpenAI ──
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # ── Whisper Transcription ──
    default_transcription_language: str = Field(
        default="vi", alias="DEFAULT_TRANSCRIPTION_LANGUAGE"
    )

    # ── WhisperLiveKit (self-hosted) ──
    whisper_livekit_url: str = Field(
        default="",
        alias="WHISPER_LIVEKIT_URL",
        description=(
            "WebSocket URL of a self-hosted WhisperLiveKit server with diarization. "
            "Example: wss://host.cloudspaces.litng.ai/asr "
            "When set, the application uses WhisperLiveKit instead of OpenAI Whisper API."
        ),
    )

    # ── Database (PostgreSQL — deprecated, use Supabase instead) ──
    postgres_url: str = Field(default="", alias="POSTGRES_URL")

    # ── Supabase ──
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    # ── Jira Integration (optional) ──
    jira_base_url: str = Field(default="", alias="JIRA_BASE_URL")
    jira_email: str = Field(default="", alias="JIRA_EMAIL")
    jira_api_token: str = Field(default="", alias="JIRA_API_TOKEN")
    jira_project_key: str = Field(default="", alias="JIRA_PROJECT_KEY")

    # ── Audio Recording ──
    audio_sample_rate: int = Field(default=16000, alias="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(default=1, alias="AUDIO_CHANNELS")
    audio_mic_enabled: bool = Field(default=True, alias="AUDIO_MIC_ENABLED")
    audio_mic_gain: float = Field(default=3.0, alias="AUDIO_MIC_GAIN")
    audio_sys_gain: float = Field(default=0.5, alias="AUDIO_SYS_GAIN")
    audio_output_dir: str = Field(default="data/recordings", alias="AUDIO_OUTPUT_DIR")
    audio_retention_hours: int = Field(
        default=24,
        alias="AUDIO_RETENTION_HOURS",
        description="Hours to retain audio files before cleanup",
    )

    # ── App Secret (Fernet key for credential encryption) ──
    app_secret_key: Optional[str] = Field(default=None, alias="APP_SECRET_KEY")

    # ── Audio Ingestion ──
    audio_max_upload_mb: int = Field(
        default=500,
        alias="AUDIO_MAX_UPLOAD_MB",
        description="Maximum upload file size in megabytes",
    )
    audio_storage_base: str = Field(
        default="data/meeting-audio",
        alias="AUDIO_STORAGE_BASE",
        description="Base directory for normalized audio storage",
    )

    # ── Chunked Transcription ──
    transcription_chunk_seconds: int = Field(
        default=60, alias="TRANSCRIPTION_CHUNK_SECONDS"
    )

    # ── Celery / Background Tasks ──
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND"
    )

    # ── Confidence Thresholds for Review Items ──
    confidence_low_threshold: float = Field(default=0.4, alias="CONFIDENCE_LOW_THRESHOLD")
    confidence_high_threshold: float = Field(default=0.7, alias="CONFIDENCE_HIGH_THRESHOLD")

    # ── HTTP Backend (Flet desktop -> FastAPI) ──
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")

    # ── CORS Configuration ──
    cors_origins: str = Field(
        default="*",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed origins, or '*' for all"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field(
        default="*",
        alias="CORS_ALLOW_METHODS",
        description="Comma-separated list of allowed HTTP methods, or '*' for all"
    )
    cors_allow_headers: str = Field(
        default="*",
        alias="CORS_ALLOW_HEADERS",
        description="Comma-separated list of allowed headers, or '*' for all"
    )

    # ── Rate Limiting ──
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_default: str = Field(
        default="100/minute",
        alias="RATE_LIMIT_DEFAULT",
        description="Default rate limit (e.g., '100/minute', '1000/hour')"
    )
    rate_limit_transcription: str = Field(
        default="10/minute",
        alias="RATE_LIMIT_TRANSCRIPTION",
        description="Rate limit for transcription endpoints (expensive operations)"
    )
    rate_limit_analysis: str = Field(
        default="20/minute",
        alias="RATE_LIMIT_ANALYSIS",
        description="Rate limit for analysis endpoints"
    )
    rate_limit_jira: str = Field(
        default="30/minute",
        alias="RATE_LIMIT_JIRA",
        description="Rate limit for Jira push endpoints"
    )

    # ── Logging ──
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_cors_methods(self) -> list[str]:
        """Parse CORS methods from comma-separated string."""
        if self.cors_allow_methods == "*":
            return ["*"]
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    def get_cors_headers(self) -> list[str]:
        """Parse CORS headers from comma-separated string."""
        if self.cors_allow_headers == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache. Useful for testing."""
    get_settings.cache_clear()


# ── Logging Setup ──
_settings = get_settings()

logging.basicConfig(
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    return logging.getLogger(name)

"""
Cấu hình tập trung + logging setup cho AI Meeting Assistant.

Dùng pydantic-settings BaseSettings + lru_cache get_settings() để validate
và cache cấu hình. Giữ các tên constant cũ làm module-level alias để
các module import trực tiếp không bị break.
"""
import logging
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    """Cấu hình ứng dụng — load từ .env + biến môi trường."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── OpenAI ──
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # ── Whisper ──
    default_transcription_language: str = Field(
        default="en", alias="DEFAULT_TRANSCRIPTION_LANGUAGE"
    )

    # ── Database ──
    postgres_url: str = Field(default="", alias="POSTGRES_URL")

    # ── Jira (optional) ──
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

    # ── App secret (Fernet key cho provider_configs encrypt — P7) ──
    app_secret_key: Optional[str] = Field(default=None, alias="APP_SECRET_KEY")

    # ── Chunked transcription (P8) ──
    transcription_chunk_seconds: int = Field(
        default=60, alias="TRANSCRIPTION_CHUNK_SECONDS"
    )

    # ── Background tasks ──
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND"
    )

    # ── Confidence thresholds ──
    confidence_low_threshold: float = Field(default=0.4, alias="CONFIDENCE_LOW_THRESHOLD")
    confidence_high_threshold: float = Field(default=0.7, alias="CONFIDENCE_HIGH_THRESHOLD")

    # ── HTTP Backend (Flet → FastAPI) ──
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")

    # ── Logging ──
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Trả về Settings singleton (cached)."""
    return Settings()


_settings = get_settings()

# ── Module-level aliases giữ backward-compat ──
OPENAI_API_KEY: str = _settings.openai_api_key
OPENAI_MODEL: str = _settings.openai_model

DEFAULT_TRANSCRIPTION_LANGUAGE: str = _settings.default_transcription_language

JIRA_BASE_URL: str = _settings.jira_base_url
JIRA_EMAIL: str = _settings.jira_email
JIRA_API_TOKEN: str = _settings.jira_api_token
JIRA_PROJECT_KEY: str = _settings.jira_project_key

AUDIO_SAMPLE_RATE: int = _settings.audio_sample_rate
AUDIO_CHANNELS: int = _settings.audio_channels
AUDIO_MIC_ENABLED: bool = _settings.audio_mic_enabled
AUDIO_MIC_GAIN: float = _settings.audio_mic_gain
AUDIO_SYS_GAIN: float = _settings.audio_sys_gain
AUDIO_OUTPUT_DIR: str = _settings.audio_output_dir

APP_SECRET_KEY: Optional[str] = _settings.app_secret_key
TRANSCRIPTION_CHUNK_SECONDS: int = _settings.transcription_chunk_seconds

LOG_LEVEL: str = _settings.log_level

POSTGRES_URL: str = _settings.postgres_url
CELERY_BROKER_URL: str = _settings.celery_broker_url
CELERY_RESULT_BACKEND: str = _settings.celery_result_backend
CONFIDENCE_LOW_THRESHOLD: float = _settings.confidence_low_threshold
CONFIDENCE_HIGH_THRESHOLD: float = _settings.confidence_high_threshold
API_BASE_URL: str = _settings.api_base_url

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Trả về logger đã được cấu hình theo tên module."""
    return logging.getLogger(name)

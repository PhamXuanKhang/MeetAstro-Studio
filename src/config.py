"""
Cấu hình tập trung + logging setup cho AI Meeting Assistant.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# ── Whisper ───────────────────────────────────────────────────────────────────
WHISPER_LOCAL_MODEL: str = os.getenv("WHISPER_LOCAL_MODEL", "base")
DEFAULT_TRANSCRIPTION_LANGUAGE: str = os.getenv("DEFAULT_TRANSCRIPTION_LANGUAGE", "vi")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/meetings.db")

# ── Jira (optional — stub mode nếu thiếu) ────────────────────────────────────
JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")

# ── Audio Recording ───────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_MIC_ENABLED: bool = os.getenv("AUDIO_MIC_ENABLED", "true").lower() == "true"
AUDIO_MIC_GAIN: float = float(os.getenv("AUDIO_MIC_GAIN", "3.0"))
AUDIO_SYS_GAIN: float = float(os.getenv("AUDIO_SYS_GAIN", "0.5"))
AUDIO_OUTPUT_DIR: str = os.getenv("AUDIO_OUTPUT_DIR", "data/recordings")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Trả về logger đã được cấu hình theo tên module."""
    return logging.getLogger(name)

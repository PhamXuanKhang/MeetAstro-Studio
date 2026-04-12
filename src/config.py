"""
Cấu hình tập trung + logging setup cho AI Meeting Assistant.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

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
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")

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

"""
Rate limiting utilities for API endpoints.

Provides decorators and helpers for applying rate limits.
Rate limits are configurable via environment variables.
"""
from functools import wraps
from typing import Callable, Optional

from src.config import get_logger, get_settings

logger = get_logger(__name__)

_limiter = None


def get_limiter():
    """Get the rate limiter instance from app state, or None if not configured."""
    return _limiter


def set_limiter(limiter) -> None:
    """Set the global limiter instance. Called during app startup."""
    global _limiter
    _limiter = limiter


def rate_limit(limit_string: Optional[str] = None):
    """
    Rate limiting decorator for FastAPI endpoints.

    If rate limiting is disabled or slowapi is not installed, this is a no-op.

    Args:
        limit_string: Rate limit string (e.g., "10/minute"). If None, uses default.

    Usage:
        @router.post("/endpoint")
        @rate_limit("10/minute")
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        settings = get_settings()
        if not settings.rate_limit_enabled:
            return func

        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address

            actual_limit = limit_string or settings.rate_limit_default

            limiter = Limiter(key_func=get_remote_address)
            decorated = limiter.limit(actual_limit)(func)
            return decorated
        except ImportError:
            return func

    return decorator


def get_rate_limit_for_endpoint(endpoint_type: str) -> str:
    """
    Get the configured rate limit for a specific endpoint type.

    Args:
        endpoint_type: One of "default", "transcription", "analysis", "jira"

    Returns:
        Rate limit string (e.g., "10/minute")
    """
    settings = get_settings()
    limits = {
        "default": settings.rate_limit_default,
        "transcription": settings.rate_limit_transcription,
        "analysis": settings.rate_limit_analysis,
        "jira": settings.rate_limit_jira,
    }
    return limits.get(endpoint_type, settings.rate_limit_default)

"""
Backend factory: HTTP-only.

Use in views:
    from frontend.core.backend_factory import get_backend
    backend = get_backend()
"""
from __future__ import annotations


def get_backend():
    """Return HttpBackend configured with API_BASE_URL."""
    try:
        from src.config import get_settings

        settings = get_settings()
        base_url = settings.api_base_url
    except Exception:
        base_url = "http://localhost:8000"

    from frontend.core.http_backend import HttpBackend

    return HttpBackend(base_url)

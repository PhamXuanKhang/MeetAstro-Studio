"""
Schemas cho Celery job status polling.
"""
from typing import Any, Optional

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    state: str  # PENDING | STARTED | SUCCESS | FAILURE | RETRY
    progress_pct: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class JiraPushResponse(BaseModel):
    job_id: Optional[str] = None
    is_stub: bool = False
    epic_keys: list[str] = []
    task_count: int = 0
    subtask_count: int = 0
    message: str = ""

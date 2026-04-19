"""
Pydantic models cho AI Meeting Assistant.
Cấu trúc: MeetingRecord → MeetingAnalysis → Epic → Task → Subtask.

Giữ nguyên API `to_dict / from_dict / to_json / from_json` để các caller
hiện tại (database, exporter, openai_analyzer) không cần thay đổi.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """Mức độ ưu tiên của action item."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class _BaseSchemaModel(BaseModel):
    """Base class cung cấp API tương thích với dataclass cũ."""

    model_config = ConfigDict(
        use_enum_values=False,
        validate_assignment=False,
        populate_by_name=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize sang dict JSON-safe (enum → string, datetime → ISO)."""
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """Serialize sang JSON string (UTF-8, indent=2)."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Parse từ dict — bỏ qua field không tồn tại."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, s: str):
        """Parse từ JSON string."""
        return cls.model_validate_json(s)


class ActionItem(_BaseSchemaModel):
    """Base cho mọi action item (Task, Subtask)."""

    summary: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None  # ISO date string: YYYY-MM-DD
    priority: Priority = Priority.MEDIUM
    context: str = ""


class Subtask(ActionItem):
    """Bước nhỏ trong một Task."""

    confidence: float = 0.0
    validation_notes: list[str] = Field(default_factory=list)


class Task(ActionItem):
    """Action item cụ thể, có thể chứa subtasks."""

    subtasks: list[Subtask] = Field(default_factory=list)
    confidence: float = 0.0
    validation_notes: list[str] = Field(default_factory=list)


class Epic(_BaseSchemaModel):
    """Chủ đề lớn / quyết định chính của cuộc họp."""

    summary: str
    description: str = ""
    tasks: list[Task] = Field(default_factory=list)


class MeetingAnalysis(_BaseSchemaModel):
    """Kết quả phân tích một cuộc họp."""

    epics: list[Epic] = Field(default_factory=list)
    summary: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    discussion_points: list[str] = Field(default_factory=list)
    parking_lot: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MeetingRecord(_BaseSchemaModel):
    """Bản ghi một cuộc họp lưu trong database."""

    title: str
    transcript: str = ""
    id: Optional[int] = None
    audio_path: Optional[str] = None
    analysis: Optional[MeetingAnalysis] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

"""
Dataclasses cho AI Meeting Assistant.
Cấu trúc: MeetingRecord → MeetingAnalysis → Epic → Task → Subtask
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Priority(str, Enum):
    """Mức độ ưu tiên của action item."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class ActionItem:
    """Base class cho mọi action item (Task, Subtask)."""
    summary: str
    assignee: Optional[str]
    deadline: Optional[str]  # ISO date string: YYYY-MM-DD
    priority: Priority
    context: str  # Trích dẫn từ transcript


@dataclass
class Subtask(ActionItem):
    """Bước nhỏ trong một Task."""

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "assignee": self.assignee,
            "deadline": self.deadline,
            "priority": self.priority.value,
            "context": self.context,
        }

    @staticmethod
    def from_dict(data: dict) -> "Subtask":
        return Subtask(
            summary=data.get("summary", ""),
            assignee=data.get("assignee"),
            deadline=data.get("deadline"),
            priority=Priority(data.get("priority", "Medium")),
            context=data.get("context", ""),
        )


@dataclass
class Task(ActionItem):
    """Action item cụ thể, có thể chứa subtasks."""
    subtasks: list[Subtask] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "assignee": self.assignee,
            "deadline": self.deadline,
            "priority": self.priority.value,
            "context": self.context,
            "subtasks": [s.to_dict() for s in self.subtasks],
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(
            summary=data.get("summary", ""),
            assignee=data.get("assignee"),
            deadline=data.get("deadline"),
            priority=Priority(data.get("priority", "Medium")),
            context=data.get("context", ""),
            subtasks=[Subtask.from_dict(s) for s in data.get("subtasks", [])],
        )


@dataclass
class Epic:
    """Chủ đề lớn / quyết định chính của cuộc họp."""
    summary: str
    description: str
    tasks: list[Task] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @staticmethod
    def from_dict(data: dict) -> "Epic":
        return Epic(
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
        )


@dataclass
class MeetingAnalysis:
    """Kết quả phân tích một cuộc họp."""
    epics: list[Epic]
    summary: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "epics": [e.to_dict() for e in self.epics],
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "MeetingAnalysis":
        created_at = data.get("created_at")
        return MeetingAnalysis(
            summary=data.get("summary", ""),
            epics=[Epic.from_dict(e) for e in data.get("epics", [])],
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(s: str) -> "MeetingAnalysis":
        return MeetingAnalysis.from_dict(json.loads(s))


@dataclass
class MeetingRecord:
    """Bản ghi một cuộc họp lưu trong database."""
    title: str
    transcript: str
    id: Optional[int] = None
    audio_path: Optional[str] = None
    analysis: Optional[MeetingAnalysis] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "audio_path": self.audio_path,
            "transcript": self.transcript,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

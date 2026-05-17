"""
MockAnalyzer — trả về MeetingAnalysis giả để test offline và fallback khi thiếu API key.
"""
from src.providers.base_analyzer import BaseAnalyzer
from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task


class MockAnalyzer(BaseAnalyzer):
    """Analyzer giả — không gọi API, dùng cho test và fallback."""

    def analyze(self, transcript: str) -> MeetingAnalysis:
        subtask = Subtask(
            summary="Chuẩn bị tài liệu",
            assignee="Unassigned",
            deadline=None,
            priority=Priority.LOW,
            context="",
            confidence=0.5,
        )
        task = Task(
            summary="Hoàn thành action items",
            assignee="Unassigned",
            deadline=None,
            priority=Priority.MEDIUM,
            context="Mock task từ transcript.",
            subtasks=[subtask],
            confidence=0.5,
        )
        epic = Epic(
            summary="Mock Epic",
            description="Epic giả sinh ra bởi MockAnalyzer.",
            tasks=[task],
        )
        return MeetingAnalysis(
            epics=[epic],
            summary="[MOCK] Cuộc họp được phân tích bằng MockAnalyzer.",
            key_decisions=["[MOCK] Quyết định ví dụ"],
            discussion_points=["[MOCK] Điểm thảo luận ví dụ"],
            parking_lot=["[MOCK] Vấn đề tạm gác ví dụ"],
        )

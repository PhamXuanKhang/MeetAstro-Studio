"""ABC cho AI analyzer providers."""
from abc import ABC, abstractmethod

from src.schema import MeetingAnalysis


class BaseAnalyzer(ABC):
    """Interface chung cho tất cả AI analyzer providers."""

    @abstractmethod
    def analyze(self, transcript: str) -> MeetingAnalysis:
        """Phân tích transcript và trả về MeetingAnalysis có cấu trúc Epic/Task/Subtask."""

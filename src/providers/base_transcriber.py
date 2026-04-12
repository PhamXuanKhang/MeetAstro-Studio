"""ABC cho transcription providers."""
from abc import ABC, abstractmethod


class BaseTranscriber(ABC):
    """Interface chung cho tất cả transcription providers."""

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        """Chuyển đổi file audio thành văn bản transcript."""

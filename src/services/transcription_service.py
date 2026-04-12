"""
Transcription service — fallback chain: Whisper API → Local Whisper.
"""
from src.config import get_logger
from src.providers.local_transcriber import LocalTranscriber
from src.providers.openai_transcriber import OpenAITranscriber

logger = get_logger(__name__)


def transcribe(audio_path: str, language: str = "vi") -> str:
    """
    Transcribe file audio sang văn bản.

    Thử OpenAI Whisper API trước. Nếu thất bại → log warning → fallback LocalTranscriber.
    Nếu cả hai đều fail → raise RuntimeError.
    """
    try:
        return OpenAITranscriber().transcribe(audio_path, language=language)
    except Exception as exc:
        logger.warning(
            "OpenAI Whisper API thất bại (%s). Đang fallback sang Local Whisper...", exc
        )

    try:
        return LocalTranscriber().transcribe(audio_path, language=language)
    except Exception as exc:
        raise RuntimeError(
            f"Cả hai transcription providers đều thất bại. Lỗi cuối: {exc}"
        ) from exc

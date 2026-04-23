"""
Transcription service — OpenAI Whisper API + Speaker Diarization.

transcribe()         : Whisper API standard transcription.
transcribe_diarized(): Whisper API với speaker diarization, fallback về transcribe().
transcribe_chunks()  : Transcribe nhiều chunk tuần tự rồi concat kết quả.
"""
from typing import List

from src.config import DEFAULT_TRANSCRIPTION_LANGUAGE, get_logger
from src.providers.openai_diarize_transcriber import OpenAIDiarizeTranscriber
from src.providers.openai_transcriber import OpenAITranscriber

logger = get_logger(__name__)


def transcribe(audio_path: str, language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
    """Transcribe file audio sang văn bản qua OpenAI Whisper API."""
    try:
        return OpenAITranscriber().transcribe(audio_path, language=language)
    except Exception as exc:
        raise RuntimeError(f"OpenAI Whisper API thất bại: {exc}") from exc


def transcribe_chunks(paths: List[str], language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
    """Transcribe từng chunk tuần tự rồi concat kết quả.

    Chunk thất bại sẽ bị bỏ qua (warning log) để không làm dừng toàn bộ pipeline.
    """
    if not paths:
        return ""

    parts: List[str] = []
    for i, path in enumerate(paths):
        logger.info("Transcribing chunk %d/%d: %s", i + 1, len(paths), path)
        try:
            text = transcribe(path, language)
            if text.strip():
                parts.append(text.strip())
        except Exception as exc:
            logger.warning("Chunk %s thất bại — bỏ qua: %s", path, exc)

    return " ".join(parts)


def transcribe_diarized(audio_path: str, language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
    """Transcribe audio kèm nhận diện người nói (Speaker Diarization).

    Dùng gpt-4o-transcribe-diarize. Nếu diarize thất bại → fallback về transcribe()
    thông thường để không làm gián đoạn workflow.

    Kết quả khi thành công:
        [Speaker 0]: Hôm nay chúng ta họp về...
        [Speaker 1]: Vâng, tôi đồng ý...
    """
    try:
        logger.info("Starting transcribe+diarize with gpt-4o-transcribe-diarize...")
        result = OpenAIDiarizeTranscriber().transcribe(audio_path, language=language)
        if result.strip():
            logger.info("Diarize succeeded: %d chars.", len(result))
            return result
        logger.warning("Diarize returned empty text — falling back to plain Whisper...")
    except Exception as exc:
        logger.warning("Diarization failed (%s) — falling back to plain Whisper...", exc)
    return transcribe(audio_path, language=language)

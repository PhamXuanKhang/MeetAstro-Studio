"""
Transcription service — fallback chain: Whisper API → Local Whisper.

Ngoài ra, hỗ trợ transcribe_diarized() dùng gpt-4o-transcribe-diarize
để nhận diện người nói, fallback về transcribe() thông thường nếu lỗi.
"""
import os
from typing import List

from src.config import get_logger
from src.providers.local_transcriber import LocalTranscriber
from src.providers.openai_diarize_transcriber import OpenAIDiarizeTranscriber
from src.providers.openai_transcriber import OpenAITranscriber

logger = get_logger(__name__)

_MAX_WHISPER_BYTES = 25 * 1024 * 1024  # 25 MB Whisper API limit


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


def _transcribe_single(audio_path: str, language: str) -> str:
    """Transcribe một file — dùng LocalTranscriber nếu vượt 25MB Whisper limit."""
    try:
        size = os.path.getsize(audio_path)
    except OSError:
        size = 0

    if size >= _MAX_WHISPER_BYTES:
        logger.warning(
            "File %s vượt 25MB (%d bytes) — dùng LocalTranscriber.", audio_path, size
        )
        return LocalTranscriber().transcribe(audio_path, language=language)

    return transcribe(audio_path, language=language)


def transcribe_chunks(paths: List[str], language: str = "vi") -> str:
    """Transcribe từng chunk tuần tự rồi concat kết quả.

    Mỗi chunk được transcribe độc lập. File vượt 25MB tự động dùng LocalTranscriber.
    Trả về full transcript ghép từ tất cả chunks.
    """
    if not paths:
        return ""

    parts: List[str] = []
    for i, path in enumerate(paths):
        logger.info("Transcribing chunk %d/%d: %s", i + 1, len(paths), path)
        try:
            text = _transcribe_single(path, language)
            if text.strip():
                parts.append(text.strip())
        except Exception as exc:
            logger.warning("Chunk %s thất bại — bỏ qua: %s", path, exc)

    return " ".join(parts)


def transcribe_diarized(audio_path: str, language: str = "vi") -> str:
    """Transcribe audio kèm nhận diện người nói (Speaker Diarization).

    Dùng gpt-4o-transcribe-diarize — tích hợp sẵn diarization, không cần model local.
    Kết quả trả về string có nhãn người nói:
        [Speaker 0]: Hôm nay chúng ta họp về...
        [Speaker 1]: Vâng, tôi đồng ý...

    Nếu API diarize thất bại → log warning → fallback về transcribe() thông thường
    (không có nhãn người nói) để không làm gián đoạn workflow.
    """
    try:
        logger.info("Đang transcribe+diarize với gpt-4o-transcribe-diarize...")
        result = OpenAIDiarizeTranscriber().transcribe(audio_path, language=language)
        logger.info("Diarize thành công: %d ký tự.", len(result))
        return result
    except Exception as exc:
        logger.warning(
            "Diarization thất bại (%s). Fallback về transcribe() thông thường...", exc
        )
        return transcribe(audio_path, language=language)

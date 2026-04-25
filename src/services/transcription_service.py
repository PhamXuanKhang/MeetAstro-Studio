"""
Transcription service - OpenAI Whisper API + Speaker Diarization.

transcribe()         : Whisper API standard transcription.
transcribe_diarized(): Whisper API with speaker diarization, fallback to transcribe().
"""
from typing import Optional

from src.config import get_logger, get_settings
from src.providers.openai_diarize_transcriber import OpenAIDiarizeTranscriber
from src.providers.openai_transcriber import OpenAITranscriber

logger = get_logger(__name__)


def transcribe(audio_path: str, language: Optional[str] = None) -> str:
    """
    Transcribe audio file to text via OpenAI Whisper API.

    Args:
        audio_path: Path to the audio file.
        language: Language code. If None, uses default from settings.

    Returns:
        Transcribed text.

    Raises:
        RuntimeError: If transcription fails.
    """
    settings = get_settings()
    actual_language = language if language is not None else settings.default_transcription_language
    try:
        return OpenAITranscriber().transcribe(audio_path, language=actual_language)
    except Exception as exc:
        raise RuntimeError(f"OpenAI Whisper API failed: {exc}") from exc


def transcribe_diarized(audio_path: str, language: Optional[str] = None) -> str:
    """
    Transcribe audio with speaker diarization (Speaker Identification).

    Uses gpt-4o-transcribe-diarize. If diarization fails, falls back to
    standard transcribe() to avoid workflow interruption.

    Output format when successful:
        [Speaker 0]: Today we're meeting about...
        [Speaker 1]: Yes, I agree...

    Args:
        audio_path: Path to the audio file.
        language: Language code. If None, uses default from settings.

    Returns:
        Transcribed text with speaker labels.
    """
    settings = get_settings()
    actual_language = language if language is not None else settings.default_transcription_language

    try:
        logger.info("Starting transcribe+diarize with gpt-4o-transcribe-diarize...")
        result = OpenAIDiarizeTranscriber().transcribe(audio_path, language=actual_language)
        if result.strip():
            logger.info("Diarization succeeded: %d chars.", len(result))
            return result
        logger.warning("Diarization returned empty text - falling back to plain Whisper...")
    except Exception as exc:
        logger.warning("Diarization failed (%s) - falling back to plain Whisper...", exc)
    return transcribe(audio_path, language=actual_language)

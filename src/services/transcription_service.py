"""
Transcription service - Whisper API + Speaker Diarization.

transcribe()         : Whisper API standard transcription.
transcribe_diarized(): Whisper API with speaker diarization, fallback to transcribe().
                       Automatically uses WhisperLiveKit when WHISPER_LIVEKIT_URL is set,
                       otherwise falls back to OpenAI gpt-4o-transcribe-diarize.
"""
from typing import Callable, Optional

from src.config import get_logger, get_settings
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

    Uses WhisperLiveKit when WHISPER_LIVEKIT_URL is configured;
    otherwise falls back to gpt-4o-transcribe-diarize.

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

    # Try WhisperLiveKit first if configured
    if settings.whisper_livekit_url:
        try:
            from src.providers.whisper_livekit_transcriber import (
                WhisperLiveKitDiarizeTranscriber,
            )
            logger.info(
                "Using WhisperLiveKit diarization: %s",
                settings.whisper_livekit_url,
            )
            result = WhisperLiveKitDiarizeTranscriber().transcribe(
                audio_path, language=actual_language
            )
            if result.strip():
                logger.info(
                    "WhisperLiveKit diarization succeeded: %d chars.",
                    len(result),
                )
                return result
            logger.warning(
                "WhisperLiveKit returned empty text - falling back to OpenAI..."
            )
        except Exception as exc:
            logger.warning(
                "WhisperLiveKit diarization failed (%s) - falling back to OpenAI...",
                exc,
            )
    else:
        logger.info("WHISPER_LIVEKIT_URL not set; using OpenAI gpt-4o-transcribe-diarize.")

    # Fallback to OpenAI
    try:
        from src.providers.openai_diarize_transcriber import OpenAIDiarizeTranscriber
        logger.info("Starting transcribe+diarize with gpt-4o-transcribe-diarize...")
        result = OpenAIDiarizeTranscriber().transcribe(audio_path, language=actual_language)
        if result.strip():
            logger.info("OpenAI diarization succeeded: %d chars.", len(result))
            return result
        logger.warning("OpenAI diarization returned empty text - falling back to plain Whisper...")
    except Exception as exc:
        logger.warning("OpenAI diarization failed (%s) - falling back to plain Whisper...", exc)
    return transcribe(audio_path, language=actual_language)


def transcribe_diarized_stream(
    audio_path: str,
    on_partial: Callable[[list[dict]], None],
    language: Optional[str] = None,
) -> list[dict]:
    """
    Stream diarization results, calling on_partial(segments) per partial result.

    Uses WhisperLiveKit when WHISPER_LIVEKIT_URL is configured.
    Raises immediately if WhisperLiveKit is not available.

    Args:
        audio_path: Path to the audio file.
        on_partial: Callback invoked each time the server sends updated lines.
                    Receives the full accumulated list of raw server lines.
        language: Language code. If None, uses default from settings.

    Returns:
        The final list of raw server lines after server signals completion.

    Raises:
        RuntimeError: If WhisperLiveKit is not configured or fails.
    """
    settings = get_settings()
    url = settings.whisper_livekit_url
    if not url:
        raise RuntimeError(
            "WHISPER_LIVEKIT_URL is not configured. "
            "Cannot stream diarization results."
        )

    from src.providers.whisper_livekit_transcriber import (
        stream_to_callback,
        _run_async,
    )

    logger.info(
        "Streaming WhisperLiveKit diarization: %s",
        url,
    )
    return _run_async(stream_to_callback(audio_path, url, on_partial))

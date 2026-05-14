"""OpenAI Whisper API transcriber."""
import time
from typing import Optional

import openai

from src.config import get_logger, get_settings
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


def _normalize_language(language: Optional[str]) -> Optional[str]:
    if language is None:
        return None
    cleaned = language.strip()
    return cleaned or None


class OpenAITranscriber(BaseTranscriber):
    """Uses OpenAI Whisper API to transcribe audio files."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the transcriber.

        Args:
            api_key: OpenAI API key. If None, loads from settings.
        """
        settings = get_settings()
        actual_api_key = api_key if api_key is not None else settings.openai_api_key
        self._client = openai.OpenAI(api_key=actual_api_key)

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file using Whisper API.

        Retries up to 3 times with exponential backoff.

        Args:
            audio_path: Path to the audio file.
            language: Language code (e.g., 'en', 'vi'). If None, OpenAI auto-detects.

        Returns:
            Transcribed text.

        Raises:
            FileNotFoundError: If audio file does not exist.
            RuntimeError: If all retry attempts fail.
        """
        actual_language = _normalize_language(language)

        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    "Transcribing via OpenAI Whisper API (attempt %d/%d)...",
                    attempt, _MAX_RETRIES
                )
                with open(audio_path, "rb") as audio_file:
                    request_kwargs = {
                        "model": "whisper-1",
                        "file": audio_file,
                    }
                    if actual_language:
                        request_kwargs["language"] = actual_language
                    response = self._client.audio.transcriptions.create(**request_kwargs)
                transcript = response.text.strip()
                logger.info("Transcription successful: %d characters.", len(transcript))
                return transcript

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Whisper API error (attempt %d): %s. Retrying in %.1fs.",
                    attempt, exc, delay
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except FileNotFoundError as exc:
                raise FileNotFoundError(f"Audio file not found: {audio_path}") from exc

        raise RuntimeError(
            f"OpenAI transcriber failed after {_MAX_RETRIES} attempts: {last_error}"
        ) from last_error

"""OpenAI Whisper API transcriber."""
import time

import openai

from src.config import DEFAULT_TRANSCRIPTION_LANGUAGE, OPENAI_API_KEY, get_logger
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


class OpenAITranscriber(BaseTranscriber):
    """Dùng Whisper API của OpenAI để transcribe audio."""

    def __init__(self, api_key: str = OPENAI_API_KEY) -> None:
        self._client = openai.OpenAI(api_key=api_key)

    def transcribe(self, audio_path: str, language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
        """Gửi file audio lên Whisper API. Retry tối đa 3 lần với exponential backoff."""
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info("Đang transcribe qua OpenAI Whisper API (attempt %d/%d)...", attempt, _MAX_RETRIES)
                with open(audio_path, "rb") as audio_file:
                    response = self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                    )
                transcript = response.text.strip()
                logger.info("Transcribe thành công: %d ký tự.", len(transcript))
                return transcript

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning("Whisper API lỗi (attempt %d): %s. Thử lại sau %.1fs.", attempt, exc, delay)
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except FileNotFoundError as exc:
                raise FileNotFoundError(f"Không tìm thấy file audio: {audio_path}") from exc

        raise RuntimeError(
            f"OpenAI transcriber thất bại sau {_MAX_RETRIES} lần thử: {last_error}"
        ) from last_error

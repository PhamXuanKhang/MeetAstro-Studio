"""OpenAI gpt-4o-transcribe-diarize provider.

Uses the `gpt-4o-transcribe-diarize` model via /v1/audio/transcriptions endpoint
to transcribe audio AND perform speaker diarization in a single API call.

Response format `diarized_json` returns a list of segments:
    [{speaker: str, start: float, end: float, text: str}, ...]

Results are converted to a string format:
    [Speaker 0]: Today we're meeting about...
    [Speaker 1]: Yes, I agree...

Inherits from BaseTranscriber for backward compatibility with all callers.
"""
import time
from typing import Optional, TypedDict

import openai

from src.config import get_logger, get_settings
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)

_MAX_RETRIES = 1
_RETRY_BASE_DELAY = 2.0
_DIARIZE_MODEL = "gpt-4o-transcribe-diarize"


class DiarizedSegment(TypedDict):
    """A conversation segment from diarization results."""

    speaker: str
    start: float
    end: float
    text: str


class OpenAIDiarizeTranscriber(BaseTranscriber):
    """Transcriber using gpt-4o-transcribe-diarize with built-in diarization.

    No local model required, no HuggingFace token needed.
    Only requires the existing OPENAI_API_KEY.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the diarization transcriber.

        Args:
            api_key: OpenAI API key. If None, loads from settings.
        """
        settings = get_settings()
        actual_api_key = api_key if api_key is not None else settings.openai_api_key
        self._client = openai.OpenAI(api_key=actual_api_key)

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio with diarization, returns speaker-labeled string.

        Output format:
            [Speaker 0]: Today we're meeting about...
            [Speaker 1]: Yes, I agree...

        Single attempt - model is expensive, no retry. API errors are raised immediately.

        Args:
            audio_path: Path to the audio file.
            language: Language code. If None, uses default from settings.

        Returns:
            Transcribed text with speaker labels.
        """
        segments = self.transcribe_to_segments(audio_path, language=language)
        return self._segments_to_string(segments)

    def transcribe_to_segments(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> list[DiarizedSegment]:
        """
        Transcribe audio and return structured segments.

        Each segment: {speaker, start, end, text}.
        Use when caller needs structured data (e.g., JSON export, analytics).

        Args:
            audio_path: Path to the audio file.
            language: Language code. If None, uses default from settings.

        Returns:
            List of diarized segments.

        Raises:
            FileNotFoundError: If audio file does not exist.
            RuntimeError: If API call fails.
        """
        settings = get_settings()
        default_lang = settings.default_transcription_language
        actual_language = language if language is not None else default_lang

        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    "Transcribing+diarizing via OpenAI (model=%s, attempt %d/%d)...",
                    _DIARIZE_MODEL,
                    attempt,
                    _MAX_RETRIES,
                )
                with open(audio_path, "rb") as audio_file:
                    response = self._client.audio.transcriptions.create(
                        model=_DIARIZE_MODEL,
                        file=audio_file,
                        language=actual_language,
                        response_format="diarized_json",
                        chunking_strategy="auto",
                    )

                segments = self._parse_response(response)
                logger.info(
                    "Diarization succeeded: %d segments, %d speakers.",
                    len(segments),
                    len({s["speaker"] for s in segments}),
                )
                return segments

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Diarize API error (attempt %d): %s. Retrying in %.1fs.",
                    attempt,
                    exc,
                    delay,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except FileNotFoundError as exc:
                raise FileNotFoundError(f"Audio file not found: {audio_path}") from exc

        raise RuntimeError(
            f"OpenAIDiarizeTranscriber failed after {_MAX_RETRIES} attempt(s): {last_error}"
        ) from last_error

    def _parse_response(self, response: object) -> list[DiarizedSegment]:
        """
        Parse response object to list of DiarizedSegment.

        OpenAI diarized_json returns 'utterances' (not 'segments').
        Falls back to 'segments' for forward-compatibility.
        """
        raw = None
        if isinstance(response, dict):
            raw = response.get("utterances") or response.get("segments") or []
        else:
            raw = getattr(response, "utterances", None) or getattr(response, "segments", None)

        if raw is None:
            logger.warning(
                "Diarize response has neither 'utterances' nor 'segments' - "
                "returning empty list."
            )
            return []

        result: list[DiarizedSegment] = []
        for seg in raw:
            if isinstance(seg, dict):
                speaker_raw = seg.get("speaker", "Unknown")
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                text = str(seg.get("text", "")).strip()
            else:
                speaker_raw = getattr(seg, "speaker", "Unknown")
                start = float(getattr(seg, "start", 0.0))
                end = float(getattr(seg, "end", 0.0))
                text = str(getattr(seg, "text", "")).strip()

            if isinstance(speaker_raw, int):
                speaker = f"Speaker {speaker_raw}"
            else:
                speaker = str(speaker_raw)

            if text:
                result.append(
                    DiarizedSegment(speaker=speaker, start=start, end=end, text=text)
                )

        return result

    @staticmethod
    def _segments_to_string(segments: list[DiarizedSegment]) -> str:
        """
        Convert segment list to speaker-labeled string.

        Output:
            [Speaker 0]: Today we're meeting about...
            [Speaker 1]: Yes, I agree...

        Adjacent segments from the same speaker are merged for readability.
        """
        if not segments:
            return ""

        lines: list[str] = []
        current_speaker = segments[0]["speaker"]
        current_parts: list[str] = [segments[0]["text"]]

        for seg in segments[1:]:
            if seg["speaker"] == current_speaker:
                current_parts.append(seg["text"])
            else:
                lines.append(f"[{current_speaker}]: {' '.join(current_parts)}")
                current_speaker = seg["speaker"]
                current_parts = [seg["text"]]

        lines.append(f"[{current_speaker}]: {' '.join(current_parts)}")
        return "\n".join(lines)

"""OpenAI analyzer for extracting action items from transcripts."""
import json
import time
from pathlib import Path
from typing import Optional

import openai

from src.config import get_logger, get_settings
from src.providers.base_analyzer import BaseAnalyzer
from src.schema import MeetingAnalysis
from src.services.language_service import detect_primary_language

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_action_items.md"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


def _load_system_prompt() -> str:
    """Load the system prompt from file."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


class OpenAIAnalyzer(BaseAnalyzer):
    """Uses an OpenAI chat model with JSON mode to analyze meeting content."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        actual_api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model if model is not None else settings.openai_model
        self._client = openai.OpenAI(api_key=actual_api_key)
        self._system_prompt = _load_system_prompt()

    def analyze(
        self,
        transcript: str,
        *,
        language_source_text: Optional[str] = None,
    ) -> MeetingAnalysis:
        """
        Analyze transcript or curated note content.

        `language_source_text` lets callers pass only the actual meeting content
        for language detection when `transcript` includes English prompt wrapper
        instructions.
        """
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info("Analyzing transcript (attempt %d/%d)...", attempt, _MAX_RETRIES)
                language = detect_primary_language(language_source_text or transcript)
                user_content = (
                    f"Detected source language: {language}.\n"
                    "You must write every user-facing JSON text field in the detected source language. "
                    "Do not translate to another language. "
                    "Ignore application UI language, field names, section labels, and developer instructions "
                    "when choosing output language.\n\n"
                    f"{transcript}"
                )
                response = self._client.chat.completions.create(
                    model=self._model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.2,
                )
                raw_json = response.choices[0].message.content or "{}"
                data = json.loads(raw_json)
                analysis = MeetingAnalysis.from_dict(data)
                logger.info("Analysis successful: %d epics.", len(analysis.epics))
                return analysis

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "OpenAI API error (attempt %d): %s. Retrying in %.1fs.",
                    attempt, exc, delay
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                raise ValueError(f"Failed to parse OpenAI analyzer response: {exc}") from exc

        raise RuntimeError(
            f"OpenAI analyzer failed after {_MAX_RETRIES} attempts: {last_error}"
        ) from last_error

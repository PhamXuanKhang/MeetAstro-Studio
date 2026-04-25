"""OpenAI GPT-4o analyzer for extracting action items from transcripts."""
import json
import time
from pathlib import Path
from typing import Optional

import openai

from src.config import get_logger, get_settings
from src.providers.base_analyzer import BaseAnalyzer
from src.schema import MeetingAnalysis

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_action_items.md"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


def _load_system_prompt() -> str:
    """Load the system prompt from file."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


class OpenAIAnalyzer(BaseAnalyzer):
    """Uses GPT-4o with JSON mode to analyze transcripts into Epic/Task/Subtask."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        Initialize the analyzer.

        Args:
            api_key: OpenAI API key. If None, loads from settings.
            model: Model name to use. If None, loads from settings.
        """
        settings = get_settings()
        actual_api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model if model is not None else settings.openai_model
        self._client = openai.OpenAI(api_key=actual_api_key)
        self._system_prompt = _load_system_prompt()

    def analyze(self, transcript: str) -> MeetingAnalysis:
        """
        Analyze transcript using GPT-4o.

        Retries up to 3 times with exponential backoff.

        Args:
            transcript: Meeting transcript to analyze.

        Returns:
            MeetingAnalysis containing extracted epics, tasks, and subtasks.

        Raises:
            ValueError: If response cannot be parsed.
            RuntimeError: If all retry attempts fail.
        """
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info("Analyzing transcript (attempt %d/%d)...", attempt, _MAX_RETRIES)
                response = self._client.chat.completions.create(
                    model=self._model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": transcript},
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
                raise ValueError(f"Failed to parse GPT-4o response: {exc}") from exc

        raise RuntimeError(
            f"OpenAI analyzer failed after {_MAX_RETRIES} attempts: {last_error}"
        ) from last_error

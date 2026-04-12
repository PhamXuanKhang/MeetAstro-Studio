"""OpenAI GPT-4o analyzer — trích xuất action items từ transcript."""
import json
import time
from pathlib import Path

import openai

from src.config import OPENAI_API_KEY, OPENAI_MODEL, get_logger
from src.providers.base_analyzer import BaseAnalyzer
from src.schema import MeetingAnalysis

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_action_items.md"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # giây


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class OpenAIAnalyzer(BaseAnalyzer):
    """Dùng GPT-4o với JSON mode để phân tích transcript thành Epic/Task/Subtask."""

    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = OPENAI_MODEL) -> None:
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._system_prompt = _load_system_prompt()

    def analyze(self, transcript: str) -> MeetingAnalysis:
        """Gọi GPT-4o để phân tích transcript. Retry tối đa 3 lần với exponential backoff."""
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info("Đang phân tích transcript (attempt %d/%d)...", attempt, _MAX_RETRIES)
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
                logger.info("Phân tích thành công: %d epics.", len(analysis.epics))
                return analysis

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning("OpenAI API lỗi (attempt %d): %s. Thử lại sau %.1fs.", attempt, exc, delay)
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                raise ValueError(f"Không parse được response từ GPT-4o: {exc}") from exc

        raise RuntimeError(f"OpenAI analyzer thất bại sau {_MAX_RETRIES} lần thử: {last_error}") from last_error

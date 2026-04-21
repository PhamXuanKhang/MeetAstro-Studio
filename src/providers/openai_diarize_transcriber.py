"""OpenAI gpt-4o-transcribe-diarize provider.

Dùng model `gpt-4o-transcribe-diarize` qua endpoint /v1/audio/transcriptions
để transcribe audio VÀ nhận diện người nói (diarization) trong một lần gọi API.

Response format `diarized_json` trả về list segments có cấu trúc:
    [{speaker: str, start: float, end: float, text: str}, ...]

Kết quả được chuyển thành string dạng:
    [Speaker 0]: Hôm nay chúng ta họp về...
    [Speaker 1]: Vâng, tôi đồng ý...

Interface kế thừa BaseTranscriber — backward compatible với toàn bộ caller.
"""
import time
from typing import TypedDict

import openai

from src.config import DEFAULT_TRANSCRIPTION_LANGUAGE, OPENAI_API_KEY, get_logger
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)

_MAX_RETRIES = 1  # Tắt retry vì model này rất đắt tiền
_RETRY_BASE_DELAY = 2.0
_DIARIZE_MODEL = "gpt-4o-transcribe-diarize"


class DiarizedSegment(TypedDict):
    """Một đoạn hội thoại từ kết quả diarization."""

    speaker: str
    start: float
    end: float
    text: str


class OpenAIDiarizeTranscriber(BaseTranscriber):
    """Transcriber dùng gpt-4o-transcribe-diarize — tích hợp sẵn diarization.

    Không cần model local, không cần HuggingFace token.
    Chỉ cần OPENAI_API_KEY hiện có.
    """

    def __init__(self, api_key: str = OPENAI_API_KEY) -> None:
        self._client = openai.OpenAI(api_key=api_key)

    # ── Public API ─────────────────────────────────────────────────────────────

    def transcribe(self, audio_path: str, language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
        """Transcribe audio có diarization, trả về string đã gắn nhãn người nói.

        Output format:
            [Speaker 0]: Hôm nay chúng ta họp về...
            [Speaker 1]: Vâng, tôi đồng ý...

        Retry tối đa 3 lần với exponential backoff khi gặp lỗi API.
        """
        segments = self.transcribe_to_segments(audio_path, language=language)
        return self._segments_to_string(segments)

    def transcribe_to_segments(
        self,
        audio_path: str,
        language: str = DEFAULT_TRANSCRIPTION_LANGUAGE,
    ) -> list[DiarizedSegment]:
        """Transcribe audio và trả về danh sách segments có cấu trúc.

        Mỗi segment: {speaker, start, end, text}.
        Dùng khi caller cần dữ liệu có cấu trúc (ví dụ: export JSON, analytics).
        """
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    "Đang transcribe+diarize qua OpenAI (model=%s, attempt %d/%d)...",
                    _DIARIZE_MODEL,
                    attempt,
                    _MAX_RETRIES,
                )
                with open(audio_path, "rb") as audio_file:
                    response = self._client.audio.transcriptions.create(
                        model=_DIARIZE_MODEL,
                        file=audio_file,
                        response_format="diarized_json",
                        # chunking_strategy="auto" BẮT BUỘC cho file > 30s
                        chunking_strategy="auto",
                    )

                segments = self._parse_response(response)
                logger.info(
                    "Diarize thành công: %d segments, %d speakers.",
                    len(segments),
                    len({s["speaker"] for s in segments}),
                )
                return segments

            except (openai.APIError, openai.RateLimitError, openai.APIConnectionError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Diarize API lỗi (attempt %d): %s. Thử lại sau %.1fs.",
                    attempt,
                    exc,
                    delay,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

            except FileNotFoundError as exc:
                raise FileNotFoundError(f"Không tìm thấy file audio: {audio_path}") from exc

        raise RuntimeError(
            f"OpenAIDiarizeTranscriber thất bại sau {_MAX_RETRIES} lần thử: {last_error}"
        ) from last_error

    # ── Private helpers ────────────────────────────────────────────────────────

    def _parse_response(self, response: object) -> list[DiarizedSegment]:
        """Parse response object → list[DiarizedSegment].

        API trả về object có attribute `segments` (hoặc dict tương đương).
        """
        raw_segments = getattr(response, "segments", None)

        if raw_segments is None:
            # Fallback: nếu response là dict
            if isinstance(response, dict):
                raw_segments = response.get("segments", [])
            else:
                logger.warning("Diarize response không có 'segments' — trả về list rỗng.")
                return []

        result: list[DiarizedSegment] = []
        for seg in raw_segments:
            # Hỗ trợ cả object lẫn dict
            if isinstance(seg, dict):
                speaker = seg.get("speaker", "Unknown")
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                text = str(seg.get("text", "")).strip()
            else:
                speaker = str(getattr(seg, "speaker", "Unknown"))
                start = float(getattr(seg, "start", 0.0))
                end = float(getattr(seg, "end", 0.0))
                text = str(getattr(seg, "text", "")).strip()

            if text:  # bỏ qua segment rỗng
                result.append(
                    DiarizedSegment(speaker=speaker, start=start, end=end, text=text)
                )

        return result

    @staticmethod
    def _segments_to_string(segments: list[DiarizedSegment]) -> str:
        """Chuyển danh sách segments thành string có nhãn người nói.

        Output:
            [Speaker 0]: Hôm nay chúng ta họp về...
            [Speaker 1]: Vâng, tôi đồng ý...

        Các đoạn liền kề cùng speaker được gộp lại để dễ đọc.
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

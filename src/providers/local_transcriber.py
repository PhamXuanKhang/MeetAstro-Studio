"""Local Whisper transcriber — fallback khi Whisper API không khả dụng."""
from src.config import DEFAULT_TRANSCRIPTION_LANGUAGE, WHISPER_LOCAL_MODEL, get_logger
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)


class LocalTranscriber(BaseTranscriber):
    """Dùng openai-whisper local để transcribe audio (fallback)."""

    def __init__(self, model_name: str = WHISPER_LOCAL_MODEL) -> None:
        self._model_name = model_name
        self._model = None  # lazy load khi cần

    def _load_model(self) -> None:
        """Load Whisper model lần đầu (lazy) để tránh load khi không cần."""
        if self._model is None:
            import whisper  # import tại runtime để tránh lỗi ImportError khi không cài

            logger.info("Đang load Whisper local model '%s'...", self._model_name)
            self._model = whisper.load_model(self._model_name)
            logger.info("Load model thành công.")

    def transcribe(self, audio_path: str, language: str = DEFAULT_TRANSCRIPTION_LANGUAGE) -> str:
        """Transcribe bằng Whisper local model."""
        self._load_model()
        logger.info("Đang transcribe local (model=%s)...", self._model_name)
        result = self._model.transcribe(audio_path, language=language)
        transcript = result.get("text", "").strip()
        logger.info("Local transcribe thành công: %d ký tự.", len(transcript))
        return transcript

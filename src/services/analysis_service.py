"""
Analysis service — orchestrate AI analyzer để phân tích transcript.
"""
from src.config import get_logger
from src.providers.openai_analyzer import OpenAIAnalyzer
from src.schema import MeetingAnalysis

logger = get_logger(__name__)


def analyze(transcript: str) -> MeetingAnalysis:
    """
    Phân tích transcript và trả về MeetingAnalysis có cấu trúc Epic/Task/Subtask.

    Hiện dùng OpenAIAnalyzer (GPT-4o). Có thể mở rộng thêm analyzer khác sau.
    """
    if not transcript.strip():
        raise ValueError("Transcript không được để trống.")

    logger.info("Bắt đầu phân tích transcript (%d ký tự)...", len(transcript))
    analyzer = OpenAIAnalyzer()
    analysis = analyzer.analyze(transcript)
    logger.info("Phân tích xong: %d epics, tổng %d tasks.",
                len(analysis.epics),
                sum(len(e.tasks) for e in analysis.epics))
    return analysis

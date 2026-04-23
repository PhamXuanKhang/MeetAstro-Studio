from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.schema import MeetingAnalysis, MeetingRecord, ReviewItem


@dataclass
class AppState:
    route: str = "home"

    audio_path: Optional[str] = None
    transcript: str = ""
    analysis: Optional[MeetingAnalysis] = None
    selected_meeting: Optional[MeetingRecord] = None

    progress_text: str = ""
    busy: bool = False

    search_query: str = ""
    cached_meetings: list[MeetingRecord] = field(default_factory=list)

    # Human-in-the-Loop review state
    review_items: list[ReviewItem] = field(default_factory=list)
    meeting_status: str = ""
    current_meeting_id: Optional[str] = None


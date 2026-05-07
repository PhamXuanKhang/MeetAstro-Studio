from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppState:
    route: str = "new_meeting"

    is_recording: bool = False
    audio_storage_path: Optional[str] = None
    transcript_segments: list[dict] = field(default_factory=list)
    analysis_result: Optional[dict] = None
    selected_meeting: Optional[dict] = None
    action_items: list[dict] = field(default_factory=list)

    progress_text: str = ""
    busy: bool = False
    processing_state: str = ""

    search_query: str = ""
    cached_meetings: list[dict] = field(default_factory=list)

    meeting_status: str = ""
    current_meeting_id: Optional[str] = None

"""
Pipeline: chain transcribe -> analyze.

Call: run_pipeline.delay(meeting_id, audio_path, diarize=False, language=None)
"""
from typing import Optional

from src.workers.celery_app import celery_app
from src.workers.tasks.analyze_task import analyze_transcript
from src.workers.tasks.transcribe_task import transcribe_audio


@celery_app.task(name="run_pipeline", queue="default")
def run_pipeline(
    meeting_id: str,
    audio_path: str,
    *,
    diarize: bool = False,
    language: Optional[str] = None,
) -> dict:
    """
    Chay pipeline tuan tu: transcribe -> analyze.

    Tra ve ket qua cua analyze_task.
    """
    transcribe_result = transcribe_audio(
        meeting_id, audio_path, diarize=diarize, language=language
    )

    analyze_result = analyze_transcript(meeting_id, transcript_id="")
    return {
        "transcribe": transcribe_result,
        "analyze": analyze_result,
    }

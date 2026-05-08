"""Tests cho WhisperLiveKitDiarizeTranscriber — mock WebSocket + ffmpeg."""
import asyncio
import json as json_lib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.whisper_livekit_transcriber import (
    DiarizedSegment,
    WhisperLiveKitDiarizeTranscriber,
    _parse_server_time,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ws_message(lines: list[dict], msg_type: str = "partial") -> str:
    """Tạo JSON message string giống server trả về."""
    return json_lib.dumps({"type": msg_type, "lines": lines})


# ── Tests: _parse_server_time ─────────────────────────────────────────────────

class TestParseServerTime:
    def test_parses_hms_format(self):
        assert _parse_server_time("00:00:05.500") == 5.5

    def test_parses_full_format(self):
        assert _parse_server_time("01:30:45.123") == pytest.approx(5445.123)

    def test_parses_zero(self):
        assert _parse_server_time("00:00:00.000") == 0.0


# ── Tests: _segments_to_string (static) ───────────────────────────────────────

class TestSegmentsToString:
    def test_basic_two_speakers(self):
        segments: list[DiarizedSegment] = [
            {"speaker": "Speaker 0", "start": 0.0, "end": 5.0, "text": "Câu A"},
            {"speaker": "Speaker 1", "start": 5.5, "end": 10.0, "text": "Câu B"},
        ]
        result = WhisperLiveKitDiarizeTranscriber._segments_to_string(segments)
        assert result == "[Speaker 0]: Câu A\n[Speaker 1]: Câu B"

    def test_empty_list(self):
        assert WhisperLiveKitDiarizeTranscriber._segments_to_string([]) == ""

    def test_adjacent_same_speaker_merged(self):
        segments: list[DiarizedSegment] = [
            {"speaker": "Speaker 0", "start": 0.0, "end": 2.0, "text": "Phần một"},
            {"speaker": "Speaker 0", "start": 2.5, "end": 5.0, "text": "phần hai"},
            {"speaker": "Speaker 1", "start": 5.5, "end": 8.0, "text": "Tôi nghe"},
        ]
        result = WhisperLiveKitDiarizeTranscriber._segments_to_string(segments)
        lines = result.split("\n")
        assert len(lines) == 2
        assert "Phần một phần hai" in lines[0]
        assert "Tôi nghe" in lines[1]

    def test_single_speaker(self):
        segments: list[DiarizedSegment] = [
            {"speaker": "Speaker 0", "start": 0.0, "end": 10.0, "text": "Toàn bộ nội dung"},
        ]
        result = WhisperLiveKitDiarizeTranscriber._segments_to_string(segments)
        assert result == "[Speaker 0]: Toàn bộ nội dung"


# ── Tests: _parse_lines ───────────────────────────────────────────────────────

class TestParseLines:
    def _make_transcriber(self) -> WhisperLiveKitDiarizeTranscriber:
        return WhisperLiveKitDiarizeTranscriber.__new__(WhisperLiveKitDiarizeTranscriber)

    def test_parses_server_format_correctly(self):
        transcriber = self._make_transcriber()
        lines = [
            {
                "speaker": 1,
                "start": "00:00:00.360",
                "end": "00:00:16.800",
                "text": " Hello everyone",
            },
            {
                "speaker": 2,
                "start": "00:00:17.680",
                "end": "00:00:21.800",
                "text": " Hard to get out of bed",
            },
        ]
        result = transcriber._parse_lines(lines)

        assert len(result) == 2
        assert result[0]["speaker"] == "Speaker 1"
        assert result[0]["start"] == pytest.approx(0.36)
        assert result[0]["end"] == pytest.approx(16.8)
        assert result[0]["text"] == "Hello everyone"
        assert result[1]["speaker"] == "Speaker 2"

    def test_skips_speaker_minus_two(self):
        transcriber = self._make_transcriber()
        lines = [
            {"speaker": -2, "start": "00:00:00.000", "end": "00:00:01.000", "text": " silence"},
            {"speaker": 0, "start": "00:00:01.000", "end": "00:00:05.000", "text": "Content"},
        ]
        result = transcriber._parse_lines(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Content"

    def test_skips_empty_text(self):
        transcriber = self._make_transcriber()
        lines = [
            {"speaker": 0, "start": "00:00:00.000", "end": "00:00:01.000", "text": ""},
            {"speaker": 1, "start": "00:00:01.000", "end": "00:00:05.000", "text": "Valid"},
        ]
        result = transcriber._parse_lines(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Valid"

    def test_strips_whitespace_from_text(self):
        transcriber = self._make_transcriber()
        lines = [
            {
                "speaker": 0,
                "start": "00:00:00.000",
                "end": "00:00:05.000",
                "text": "  Leading and trailing  ",
            },
        ]
        result = transcriber._parse_lines(lines)
        assert result[0]["text"] == "Leading and trailing"

    def test_parses_string_speaker(self):
        transcriber = self._make_transcriber()
        lines = [
            {"speaker": "A", "start": "00:00:00.000", "end": "00:00:05.000", "text": "Text"},
        ]
        result = transcriber._parse_lines(lines)
        assert result[0]["speaker"] == "A"


# ── Tests: transcribe_to_segments ───────────────────────────────────────────────

class TestTranscribeToSegments:
    def _mock_settings(self, url: str = "wss://test/asr"):
        mock_settings = MagicMock()
        mock_settings.whisper_livekit_url = url
        return mock_settings

    def test_raises_on_missing_file(self):
        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings()
            transcriber = WhisperLiveKitDiarizeTranscriber()

        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.transcribe_to_segments("/nonexistent/file.wav")

    def test_raises_when_url_not_configured(self):
        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings(url="")
            with pytest.raises(ValueError, match="WHISPER_LIVEKIT_URL"):
                WhisperLiveKitDiarizeTranscriber()

    def test_uses_custom_url_when_provided(self):
        custom_url = "wss://custom-host.example.com/asr"
        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings(
                url="wss://ignored.example.com"
            )
            transcriber = WhisperLiveKitDiarizeTranscriber(url=custom_url)
            assert transcriber._url == custom_url

    def test_retries_on_websocket_failure(self):
        import websockets

        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings()
            transcriber = WhisperLiveKitDiarizeTranscriber()

        with patch(
            "src.providers.whisper_livekit_transcriber.asyncio"
        ) as mock_asyncio, patch(
            "src.providers.whisper_livekit_transcriber.time.sleep"
        ) as mock_sleep, patch(
            "src.providers.whisper_livekit_transcriber.os.path.exists",
            return_value=True,
        ):
            # First call raises, second call succeeds
            recovered_lines = [
                {"speaker": 0, "start": "00:00:00.000",
                 "end": "00:00:05.000", "text": "Recovered"}
            ]
            mock_asyncio.run.side_effect = [
                websockets.WebSocketException("Connection failed"),
                recovered_lines,
            ]

            result = transcriber.transcribe_to_segments("audio.wav")

            assert len(result) == 1
            assert result[0]["text"] == "Recovered"
            assert mock_sleep.call_count == 1

    def test_raises_after_max_retries(self):
        import websockets

        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings()
            transcriber = WhisperLiveKitDiarizeTranscriber()

        with patch(
            "src.providers.whisper_livekit_transcriber.asyncio"
        ) as mock_asyncio, patch(
            "src.providers.whisper_livekit_transcriber.time.sleep"
        ), patch(
            "src.providers.whisper_livekit_transcriber.os.path.exists",
            return_value=True,
        ):
            mock_asyncio.run.side_effect = websockets.WebSocketException(
                "Always fails"
            )

            with pytest.raises(RuntimeError, match="failed after 2 attempt"):
                transcriber.transcribe_to_segments("audio.wav")


# ── Tests: transcribe (string output) ─────────────────────────────────────────

class TestTranscribe:
    def _mock_settings(self, url: str = "wss://test/asr"):
        mock_settings = MagicMock()
        mock_settings.whisper_livekit_url = url
        return mock_settings

    def test_transcribe_returns_labeled_string(self):
        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings()
            transcriber = WhisperLiveKitDiarizeTranscriber()

        with patch.object(transcriber, "transcribe_to_segments") as mock_seg:
            mock_seg.return_value = [
                {"speaker": "Speaker 0", "start": 0.0, "end": 5.0, "text": "Câu A"},
                {"speaker": "Speaker 1", "start": 5.5, "end": 10.0, "text": "Câu B"},
            ]
            result = transcriber.transcribe("audio.wav")

        assert "[Speaker 0]: Câu A" in result
        assert "[Speaker 1]: Câu B" in result

    def test_empty_segments_returns_empty_string(self):
        with patch(
            "src.providers.whisper_livekit_transcriber.get_settings",
            autospec=True,
        ) as mock_get_settings:
            mock_get_settings.return_value = self._mock_settings()
            transcriber = WhisperLiveKitDiarizeTranscriber()

        with patch.object(transcriber, "transcribe_to_segments", return_value=[]):
            result = transcriber.transcribe("audio.wav")

        assert result == ""


# ── Tests: stream_to_callback ──────────────────────────────────────────────────

def _make_lines(speaker: int, text: str) -> list[dict]:
    """Build a mock server lines payload."""
    return [
        {
            "speaker": speaker,
            "start": "00:00:00.000",
            "end": "00:00:05.000",
            "text": text,
        }
    ]


def _make_mock_ws_ctx(recv_messages: list[str]) -> MagicMock:
    """Build a fully async-context-manager-compatible mock for websockets.connect."""
    mock_ws = MagicMock()
    mock_ws.recv = AsyncMock(side_effect=recv_messages)
    mock_ws.send = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    return mock_ctx


class TestStreamToCallback:
    """Test the streaming callback-based transcription function."""

    def test_calls_callback_on_each_partial(self):
        from src.providers.whisper_livekit_transcriber import stream_to_callback

        partials_received: list[list[dict]] = []

        def on_partial(lines: list[dict]) -> None:
            partials_received.append(list(lines))

        first_lines = _make_lines(0, "First partial")
        final_lines = _make_lines(0, "Final")

        mock_ws = MagicMock()
        mock_ws.recv = AsyncMock(side_effect=[
            _make_ws_message(first_lines, "partial"),
            _make_ws_message(first_lines, "partial"),
            _make_ws_message(final_lines, "ready_to_stop"),
        ])
        mock_ws.send = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read = MagicMock(side_effect=[b"chunk1", b""])

        with patch(
            "src.providers.whisper_livekit_transcriber.os.path.exists",
            return_value=True,
        ), patch(
            "src.providers.whisper_livekit_transcriber.websockets.connect",
            return_value=mock_ctx,
        ), patch(
            "src.providers.whisper_livekit_transcriber._run_ffmpeg_to_pcm",
            return_value=mock_proc,
        ):
            # stream_to_callback is an async function — asyncio.run executes it
            # with mocked websockets.connect, so it runs the real async logic
            result = asyncio.run(stream_to_callback(
                "audio.wav", "wss://test/asr", on_partial
            ))

        assert len(partials_received) == 2
        assert partials_received[0][0]["text"] == "First partial"
        # result is the accumulated lines from the last server message
        assert result[0]["text"] in ("First partial", "Final")
        assert mock_ws.send.call_count >= 2

    def test_raises_on_missing_file(self):
        from src.providers.whisper_livekit_transcriber import stream_to_callback

        with patch(
            "src.providers.whisper_livekit_transcriber.os.path.exists",
            return_value=False,
        ):
            with pytest.raises(FileNotFoundError):
                asyncio.run(stream_to_callback(
                    "/nonexistent.wav", "wss://test/asr", lambda _: None
                ))

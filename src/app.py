"""
AI Meeting Assistant — Streamlit UI entry point.
Workflow: Upload/Record audio → Transcribe → Analyze → Export / Save / Push to Jira
"""
import asyncio
import tempfile
import time
from pathlib import Path

import streamlit as st

from src.config import get_logger
from src.modules.database import (
    create_meeting,
    delete_provider_config,
    get_provider_config,
    init_db,
    list_meetings,
    list_provider_configs,
    set_provider_config,
)
from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import MeetingRecord
from src.services.analysis_service import analyze
from src.services.recording_service import (
    elapsed_seconds,
    is_recording,
    start_recording,
    stop_recording,
)
from src.services.jira_service import push_analysis_to_jira
from src.services.summarization_service import generate_summary_stream
from src.services.transcription_service import transcribe, transcribe_diarized

from dotenv import load_dotenv
load_dotenv()

logger = get_logger(__name__)

# ── Khởi tạo DB khi app start ─────────────────────────────────────────────────
init_db()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Meeting Assistant",
    page_icon="🎙️",
    layout="wide",
)

st.title("🎙️ AI Meeting Assistant")
st.caption("Ghi âm → Whisper transcribe → GPT-4o phân tích → Epic / Task / Subtask")

# ── Session state defaults ────────────────────────────────────────────────────
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "streaming_summary" not in st.session_state:
    st.session_state.streaming_summary = ""


# ── Helper: confidence badge ──────────────────────────────────────────────────
def _confidence_badge(confidence: float) -> str:
    """Render inline HTML badge với màu theo ngưỡng confidence."""
    pct = f"{confidence:.0%}"
    if confidence >= 0.7:
        color = "#2ecc71"  # green
    elif confidence >= 0.4:
        color = "#f39c12"  # yellow/orange
    else:
        color = "#e74c3c"  # red
    return (
        f'<span style="background:{color};color:#fff;padding:1px 6px;'
        f'border-radius:4px;font-size:0.75em;font-weight:600">'
        f'confidence: {pct}</span>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — lịch sử cuộc họp + Integrations
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("📋 Lịch sử cuộc họp")
    if st.button("🔄 Làm mới", use_container_width=True):
        st.rerun()
    try:
        records = list_meetings()
        if records:
            for rec in records:
                with st.expander(f"📝 {rec.title}", expanded=False):
                    st.caption(f"ID: {rec.id} | {rec.created_at.strftime('%d/%m/%Y %H:%M')}")
                    st.caption(f"Transcript: {len(rec.transcript)} ký tự")
                    if rec.analysis:
                        n_epics = len(rec.analysis.epics)
                        n_tasks = sum(len(e.tasks) for e in rec.analysis.epics)
                        st.caption(f"Epics: {n_epics} | Tasks: {n_tasks}")
        else:
            st.info("Chưa có cuộc họp nào được lưu.")
    except Exception as exc:
        st.error(f"Lỗi tải lịch sử: {exc}")

    # ── Integrations ──────────────────────────────────────────────────────
    st.divider()
    with st.expander("⚙️ Integrations", expanded=False):
        _PROVIDERS = ["jira", "trello", "notion", "slack", "teams"]

        try:
            _configured = {row["provider_name"] for row in list_provider_configs()}
        except Exception:
            _configured = set()

        selected_provider = st.selectbox(
            "Provider",
            _PROVIDERS,
            format_func=lambda p: f"{'✓ ' if p in _configured else ''}{p.capitalize()}",
        )

        if selected_provider in _configured:
            st.success(f"✓ {selected_provider.capitalize()} đã được cấu hình")
            if st.button(f"Xóa cấu hình {selected_provider.capitalize()}", use_container_width=True):
                try:
                    delete_provider_config(selected_provider)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Lỗi xóa config: {exc}")
        else:
            st.caption(f"{selected_provider.capitalize()} chưa được cấu hình")

        with st.form(f"provider_form_{selected_provider}"):
            st.markdown(f"**Cấu hình {selected_provider.capitalize()}**")

            if selected_provider == "jira":
                f_url = st.text_input("Base URL", placeholder="https://yourcompany.atlassian.net")
                f_email = st.text_input("Email")
                f_token = st.text_input("API Token", type="password")
                f_project = st.text_input("Project Key", placeholder="PROJ")
                config_fields = {"url": f_url, "email": f_email, "token": f_token, "project_key": f_project}
            elif selected_provider == "trello":
                f_key = st.text_input("API Key")
                f_token = st.text_input("Token", type="password")
                f_board = st.text_input("Board ID")
                config_fields = {"api_key": f_key, "token": f_token, "board_id": f_board}
            elif selected_provider == "notion":
                f_token = st.text_input("Integration Token", type="password")
                f_db = st.text_input("Database ID")
                config_fields = {"token": f_token, "database_id": f_db}
            elif selected_provider == "slack":
                f_token = st.text_input("Bot Token", type="password")
                f_channel = st.text_input("Channel ID", placeholder="#meeting-notes")
                config_fields = {"token": f_token, "channel": f_channel}
            else:  # teams
                f_webhook = st.text_input("Webhook URL", type="password")
                config_fields = {"webhook_url": f_webhook}

            submitted = st.form_submit_button("💾 Lưu cấu hình", use_container_width=True)
            if submitted:
                non_empty = {k: v for k, v in config_fields.items() if v and v.strip()}
                if not non_empty:
                    st.warning("Vui lòng điền ít nhất một trường.")
                else:
                    try:
                        set_provider_config(selected_provider, non_empty)
                        st.success(f"Đã lưu cấu hình {selected_provider.capitalize()}!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi lưu config: {exc}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — 3 cột: Upload / Transcript / Analysis
# ══════════════════════════════════════════════════════════════════════════════
col_upload, col_transcript, col_analysis = st.columns([1, 1.2, 1.5])

# ── Cột 1: Audio Input ────────────────────────────────────────────────────────
with col_upload:
    st.subheader("1️⃣ Audio Input")
    meeting_title = st.text_input("Tên cuộc họp", placeholder="Vd: Họp sprint planning 15/01")

    audio_mode = st.radio(
        "Chọn nguồn audio",
        ["📁 Upload File", "🔴 Record System Audio"],
        horizontal=True,
    )

    if audio_mode == "📁 Upload File":
        # ── Existing upload flow ──────────────────────────────────────
        uploaded_file = st.file_uploader(
            "Chọn file ghi âm",
            type=["wav", "mp3", "m4a", "ogg", "flac"],
            help="Hỗ trợ WAV, MP3, M4A, OGG, FLAC",
        )

        if uploaded_file is not None:
            suffix = Path(uploaded_file.name).suffix
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(uploaded_file.read())
            tmp.flush()
            tmp.close()
            st.session_state.audio_path = tmp.name
            st.audio(uploaded_file)
            st.caption(f"File: {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

    else:
        # ── Record System Audio flow ──────────────────────────────────
        recording_active = is_recording()

        if not recording_active:
            if st.button("⏺️ Bắt đầu ghi âm", use_container_width=True, type="primary"):
                try:
                    wav_path = start_recording()
                    st.session_state.audio_path = wav_path
                    st.rerun()
                except Exception as exc:
                    st.error(f"Lỗi bắt đầu ghi âm: {exc}")
                    logger.error("start_recording failed: %s", exc)
        else:
            # Show elapsed time
            elapsed = elapsed_seconds()
            mins, secs = divmod(int(elapsed), 60)
            st.markdown(
                f"### 🔴 Đang ghi âm: `{mins:02d}:{secs:02d}`"
            )

            if st.button("⏹️ Dừng ghi âm", use_container_width=True, type="primary"):
                try:
                    wav_path = stop_recording()
                    st.session_state.audio_path = wav_path
                    st.success(f"Đã lưu: {wav_path}")
                except Exception as exc:
                    st.error(f"Lỗi dừng ghi âm: {exc}")
                    logger.error("stop_recording failed: %s", exc)
            else:
                # Auto-refresh to update the timer display
                time.sleep(1)
                st.rerun()

        # Show current recording path if set
        if st.session_state.audio_path and not recording_active:
            st.caption(f"📂 File: {st.session_state.audio_path}")

    # Checkbox diarization — hiện luôn vì dùng cùng OPENAI_API_KEY
    use_diarization = st.checkbox(
        "👥 Nhận diện người nói (Diarization)",
        value=False,
        help="Dùng gpt-4o-transcribe-diarize — chậm hơn ~2-3x nhưng phân biệt rõ ai nói gì.",
    )

    transcribe_btn = st.button(
        "🎤 Transcribe",
        disabled=(st.session_state.audio_path is None) or is_recording(),
        use_container_width=True,
        type="primary",
    )

# ── Cột 2: Transcript ─────────────────────────────────────────────────────────
with col_transcript:
    st.subheader("2️⃣ Transcript")

    if transcribe_btn and st.session_state.audio_path:
        spinner_msg = "Đang transcribe+diarize..." if use_diarization else "Đang transcribe..."
        with st.spinner(spinner_msg):
            try:
                if use_diarization:
                    text = transcribe_diarized(st.session_state.audio_path)
                else:
                    text = transcribe(st.session_state.audio_path)
                st.session_state.transcript = text
                if use_diarization:
                    st.success("👥 Transcribe + Diarize thành công!")
                else:
                    st.success("Transcribe thành công!")
            except Exception as exc:
                st.error(f"Lỗi transcribe: {exc}")
                logger.error("Transcribe thất bại: %s", exc)

    transcript_text = st.text_area(
        "Nội dung transcript (có thể chỉnh sửa trước khi phân tích)",
        value=st.session_state.transcript,
        height=350,
        placeholder="Transcript sẽ hiển thị ở đây sau khi transcribe...",
    )
    # Cập nhật session state nếu user sửa tay
    st.session_state.transcript = transcript_text

    analyze_btn = st.button(
        "🤖 Phân tích",
        disabled=not transcript_text.strip(),
        use_container_width=True,
        type="primary",
    )

# ── Cột 3: Kết quả phân tích ─────────────────────────────────────────────────
with col_analysis:
    st.subheader("3️⃣ Kết quả phân tích")

    if analyze_btn and transcript_text.strip():
        # Streaming summary trước khi analyze() chạy đầy đủ
        summary_placeholder = st.empty()
        summary_placeholder.markdown("*Đang tạo tóm tắt...*")
        st.session_state.streaming_summary = ""

        async def _stream_summary() -> str:
            accumulated = ""
            async for token in generate_summary_stream(transcript_text):
                accumulated += token
                summary_placeholder.markdown(f"**Tóm tắt (đang tạo...):** {accumulated}▌")
            return accumulated

        try:
            streamed = asyncio.run(_stream_summary())
            st.session_state.streaming_summary = streamed
        except Exception as exc:
            logger.warning("Streaming summary lỗi: %s", exc)
            summary_placeholder.empty()

        with st.spinner("Đang phân tích cấu trúc bằng GPT-4o..."):
            try:
                analysis = analyze(transcript_text)
                # Gán lại summary từ streaming nếu analyze() không trả về summary
                if not analysis.summary and st.session_state.streaming_summary:
                    object.__setattr__(analysis, "summary", st.session_state.streaming_summary)
                st.session_state.analysis = analysis
                summary_placeholder.empty()
                st.success(f"Phân tích xong: {len(analysis.epics)} epics!")
            except Exception as exc:
                st.error(f"Lỗi phân tích: {exc}")
                logger.error("Phân tích thất bại: %s", exc)

    if st.session_state.analysis:
        analysis = st.session_state.analysis

        # Hiển thị summary
        if analysis.summary:
            st.markdown(f"**Tóm tắt:** {analysis.summary}")

        # Key decisions
        if analysis.key_decisions:
            with st.expander("📌 Quyết định chính", expanded=False):
                for decision in analysis.key_decisions:
                    st.markdown(f"- {decision}")

        # Parking lot
        if analysis.parking_lot:
            with st.expander("🅿️ Parking Lot", expanded=False):
                for item in analysis.parking_lot:
                    st.markdown(f"- {item}")

        st.divider()

        for i, epic in enumerate(analysis.epics, 1):
            with st.expander(f"🏔️ Epic {i}: {epic.summary}", expanded=True):
                if epic.description:
                    st.caption(epic.description)
                for j, task in enumerate(epic.tasks, 1):
                    badge_html = _confidence_badge(task.confidence) if task.confidence > 0 else ""
                    st.markdown(
                        f"**Task {i}.{j}:** {task.summary} {badge_html}  \n"
                        f"👤 {task.assignee or 'TBD'} | "
                        f"📅 {task.deadline or 'N/A'} | "
                        f"🔥 {task.priority.value}",
                        unsafe_allow_html=True,
                    )
                    if task.context:
                        st.caption(f"💬 {task.context}")
                    if task.validation_notes:
                        st.caption(f"📋 {' | '.join(task.validation_notes)}")
                    for k, subtask in enumerate(task.subtasks, 1):
                        sub_badge = _confidence_badge(subtask.confidence) if subtask.confidence > 0 else ""
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;↳ **Subtask {i}.{j}.{k}:** "
                            f"{subtask.summary} {sub_badge}  "
                            f"({subtask.assignee or 'TBD'} | {subtask.priority.value})",
                            unsafe_allow_html=True,
                        )

# ══════════════════════════════════════════════════════════════════════════════
# ACTION BAR — Export / Save / Jira
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.analysis:
    st.divider()
    st.subheader("4️⃣ Actions")
    analysis = st.session_state.analysis

    action_cols = st.columns(5)

    # Export Markdown
    with action_cols[0]:
        md_content = export_markdown(analysis)
        st.download_button(
            "📄 Tải Markdown",
            data=md_content.encode("utf-8"),
            file_name="meeting_analysis.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Export JSON
    with action_cols[1]:
        json_content = export_json(analysis)
        st.download_button(
            "📦 Tải JSON",
            data=json_content.encode("utf-8"),
            file_name="meeting_analysis.json",
            mime="application/json",
            use_container_width=True,
        )

    # Export CSV
    with action_cols[2]:
        csv_content = export_csv(analysis)
        st.download_button(
            "📊 Tải CSV",
            data=csv_content.encode("utf-8"),
            file_name="meeting_analysis.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Save to DB
    with action_cols[3]:
        if st.button("💾 Lưu vào DB", use_container_width=True):
            if not meeting_title.strip():
                st.warning("Vui lòng nhập tên cuộc họp.")
            else:
                try:
                    record = MeetingRecord(
                        title=meeting_title.strip(),
                        transcript=st.session_state.transcript,
                        audio_path=st.session_state.audio_path,
                        analysis=analysis,
                    )
                    new_id = create_meeting(record)
                    st.success(f"Đã lưu! ID: {new_id}")
                    logger.info("Saved meeting id=%d: '%s'", new_id, meeting_title)
                except Exception as exc:
                    st.error(f"Lỗi lưu DB: {exc}")

    # Push to Jira
    with action_cols[4]:
        if st.button("🚀 Đẩy lên Jira", use_container_width=True):
            with st.spinner("Đang đẩy lên Jira..."):
                try:
                    jira_result = push_analysis_to_jira(analysis)
                    if jira_result.is_stub:
                        st.warning("Jira STUB mode — chưa gửi API thật. Cấu hình JIRA_* trong .env hoặc Integrations sidebar.")
                    else:
                        st.success(
                            "Đẩy lên Jira thành công! "
                            f"Epics: {', '.join(jira_result.epic_keys)} | "
                            f"Tasks: {jira_result.task_count} | "
                            f"Subtasks: {jira_result.subtask_count}"
                        )
                except Exception as exc:
                    st.error(f"Lỗi Jira: {exc}")

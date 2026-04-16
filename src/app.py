"""
AI Meeting Assistant — Streamlit UI entry point.
Workflow: Upload audio → Transcribe → Analyze → Export / Save / Push to Jira
"""
import tempfile
from pathlib import Path

import streamlit as st

from src.config import get_logger
from src.modules.database import create_meeting, init_db, list_meetings
from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import MeetingRecord
from src.services.analysis_service import analyze
from src.services.jira_service import push_analysis_to_jira
from src.services.transcription_service import transcribe

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

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — lịch sử cuộc họp
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

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — 3 cột: Upload / Transcript / Analysis
# ══════════════════════════════════════════════════════════════════════════════
col_upload, col_transcript, col_analysis = st.columns([1, 1.2, 1.5])

# ── Cột 1: Upload audio ───────────────────────────────────────────────────────
with col_upload:
    st.subheader("1️⃣ Upload Audio")
    uploaded_file = st.file_uploader(
        "Chọn file ghi âm",
        type=["wav", "mp3", "m4a", "ogg", "flac"],
        help="Hỗ trợ WAV, MP3, M4A, OGG, FLAC",
    )
    meeting_title = st.text_input("Tên cuộc họp", placeholder="Vd: Họp sprint planning 15/01")

    if uploaded_file is not None:
        # Lưu tạm file để gửi cho transcriber
        suffix = Path(uploaded_file.name).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(uploaded_file.read())
        tmp.flush()
        tmp.close()
        st.session_state.audio_path = tmp.name
        st.audio(uploaded_file)
        st.caption(f"File: {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

    transcribe_btn = st.button(
        "🎤 Transcribe",
        disabled=uploaded_file is None,
        use_container_width=True,
        type="primary",
    )

# ── Cột 2: Transcript ─────────────────────────────────────────────────────────
with col_transcript:
    st.subheader("2️⃣ Transcript")

    if transcribe_btn and st.session_state.audio_path:
        with st.spinner("Đang transcribe..."):
            try:
                text = transcribe(st.session_state.audio_path)
                st.session_state.transcript = text
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
        with st.spinner("Đang phân tích bằng GPT-4o..."):
            try:
                analysis = analyze(transcript_text)
                st.session_state.analysis = analysis
                st.success(f"Phân tích xong: {len(analysis.epics)} epics!")
            except Exception as exc:
                st.error(f"Lỗi phân tích: {exc}")
                logger.error("Phân tích thất bại: %s", exc)

    if st.session_state.analysis:
        analysis = st.session_state.analysis

        st.markdown(f"**Tóm tắt:** {analysis.summary}")
        st.divider()

        for i, epic in enumerate(analysis.epics, 1):
            with st.expander(f"🏔️ Epic {i}: {epic.summary}", expanded=True):
                if epic.description:
                    st.caption(epic.description)
                for j, task in enumerate(epic.tasks, 1):
                    st.markdown(
                        f"**Task {i}.{j}:** {task.summary}  \n"
                        f"👤 {task.assignee or 'TBD'} | "
                        f"📅 {task.deadline or 'N/A'} | "
                        f"🔥 {task.priority.value}"
                    )
                    if task.context:
                        st.caption(f"💬 {task.context}")
                    for k, subtask in enumerate(task.subtasks, 1):
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;↳ **Subtask {i}.{j}.{k}:** {subtask.summary}  "
                            f"({subtask.assignee or 'TBD'} | {subtask.priority.value})"
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
                        st.warning("Jira STUB mode — chưa gửi API thật. Cấu hình JIRA_* trong .env.")
                    else:
                        st.success(
                            "Đẩy lên Jira thành công! "
                            f"Epics: {', '.join(jira_result.epic_keys)} | "
                            f"Tasks: {jira_result.task_count} | "
                            f"Subtasks: {jira_result.subtask_count}"
                        )
                except Exception as exc:
                    st.error(f"Lỗi Jira: {exc}")

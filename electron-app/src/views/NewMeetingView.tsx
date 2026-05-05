import { useState, useCallback, useRef } from 'react'
import { useAppStore } from '../store/appStore'
import { createMeeting, uploadAndTranscribe, updateTranscript, analyzeTranscript } from '../api/meetings'
import { exportMarkdown, exportJson, exportCsv } from '../api/exports'
import { useRecording } from '../hooks/useRecording'
import { useFileDialog } from '../hooks/useFileDialog'
import StepBadge from '../components/StepBadge'
import type { MeetingResponse } from '../types/schema'

interface Props {
  onOpenResults: (meeting: MeetingResponse) => void
  onOpenReview: () => void
  setBusy: (busy: boolean, text?: string) => void
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export default function NewMeetingView({ onOpenResults, onOpenReview, setBusy }: Props) {
  const {
    audioPath, setAudioPath,
    transcript, setTranscript,
    analysis, setAnalysis,
    currentMeetingId, setCurrentMeetingId,
    setSelectedMeeting,
  } = useAppStore()

  const [title, setTitle] = useState('')
  const [diarize, setDiarize] = useState(false)
  const [editableTranscript, setEditableTranscript] = useState(transcript)
  const [transcribing, setTranscribing] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [transcribeProgress, setTranscribeProgress] = useState('')
  const [analyzeProgress, setAnalyzeProgress] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const { isRecording, elapsedSeconds, error: recError, startRecording, stopRecording } = useRecording()
  const { openFile, saveFile } = useFileDialog()

  const hasAudio = !!audioPath
  const hasTranscript = editableTranscript.length > 0
  const hasAnalysis = !!analysis

  const currentStep: 1 | 2 | 3 = hasAnalysis ? 3 : hasTranscript ? 2 : 1

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  // Đảm bảo meeting đã được tạo, trả về meeting_id
  const ensureMeetingId = useCallback(async (): Promise<string> => {
    if (currentMeetingId) return currentMeetingId
    const meetingTitle = title.trim() || `Meeting ${new Date().toLocaleString('vi-VN')}`
    const meeting = await createMeeting(meetingTitle)
    setCurrentMeetingId(meeting.id)
    setSelectedMeeting(meeting)
    return meeting.id
  }, [currentMeetingId, title, setCurrentMeetingId, setSelectedMeeting])

  // Ghi âm
  const handleStartRecord = useCallback(async () => {
    setError(null)
    const path = await startRecording()
    if (path) setAudioPath(path)
    else if (recError) setError(recError)
  }, [startRecording, setAudioPath, recError])

  const handleStopRecord = useCallback(async () => {
    const path = await stopRecording()
    if (path) {
      setAudioPath(path)
      showToast('Đã dừng ghi âm. File: ' + path.split(/[\\/]/).pop())
    }
  }, [stopRecording, setAudioPath])

  // Upload file audio
  const handlePickFile = useCallback(async () => {
    const path = await openFile([{ name: 'Audio Files', extensions: ['wav', 'mp3', 'm4a', 'ogg', 'flac'] }])
    if (path) {
      setAudioPath(path)
      showToast('Đã chọn file: ' + path.split(/[\\/]/).pop())
    }
  }, [openFile, setAudioPath])

  // Bước 2: Transcribe
  const handleTranscribe = useCallback(async () => {
    if (!audioPath) { setError('Chưa có file audio.'); return }
    setError(null)
    setTranscribing(true)
    setBusy(true, 'Đang chuyển đổi âm thanh...')

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const meetingId = await ensureMeetingId()

      let fileBytes: ArrayBuffer
      if (audioPath.startsWith('blob:')) {
        const resp = await fetch(audioPath)
        fileBytes = await resp.arrayBuffer()
      } else {
        const electronAPI = (window as unknown as { electronAPI?: { readFileBytes: (path: string) => Promise<ArrayBuffer> } }).electronAPI
        if (!electronAPI?.readFileBytes) {
          throw new Error('Không thể đọc file local: Electron file bridge chưa sẵn sàng.')
        }
        fileBytes = await electronAPI.readFileBytes(audioPath)
      }

      setTranscribeProgress('Đang upload...')
      const transcript = await uploadAndTranscribe(
        meetingId,
        audioPath,
        fileBytes,
        diarize,
        'vi',
        controller.signal,
        (job) => setTranscribeProgress(`Đang xử lý... (${job.state})`)
      )

      setTranscript(transcript.raw_text)
      setEditableTranscript(transcript.raw_text)
      showToast('Transcription hoàn thành!')
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setTranscribing(false)
      setTranscribeProgress('')
      setBusy(false)
    }
  }, [audioPath, diarize, ensureMeetingId, setTranscript, setBusy])

  // Bước 3: Analyze
  const handleAnalyze = useCallback(async () => {
    if (!editableTranscript.trim()) { setError('Transcript trống.'); return }
    setError(null)
    setAnalyzing(true)
    setBusy(true, 'Đang phân tích với GPT-4o...')

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const meetingId = await ensureMeetingId()

      // Lưu transcript hiện tại (có thể user đã edit)
      await updateTranscript(meetingId, editableTranscript)
      setTranscript(editableTranscript)

      setAnalyzeProgress('Đang phân tích...')
      const analysisResp = await analyzeTranscript(
        meetingId,
        controller.signal,
        (job) => setAnalyzeProgress(`Đang phân tích... (${job.state})`)
      )

      setAnalysis(analysisResp.analysis_json)

      // Fetch meeting để update selectedMeeting
      const { getMeeting } = await import('../api/meetings')
      const meeting = await getMeeting(meetingId)
      setSelectedMeeting(meeting)

      showToast('Phân tích hoàn thành! Chuyển đến Results...')
      setTimeout(() => onOpenResults(meeting), 800)
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAnalyzing(false)
      setAnalyzeProgress('')
      setBusy(false)
    }
  }, [editableTranscript, ensureMeetingId, setTranscript, setAnalysis, setSelectedMeeting, onOpenResults, setBusy])

  // Export
  const handleExport = useCallback(async (type: 'markdown' | 'json' | 'csv') => {
    if (!currentMeetingId) { showToast('Chưa có meeting.'); return }
    try {
      let content: string
      let ext: string
      if (type === 'markdown') { content = await exportMarkdown(currentMeetingId); ext = 'md' }
      else if (type === 'json') { content = await exportJson(currentMeetingId); ext = 'json' }
      else { content = await exportCsv(currentMeetingId); ext = 'csv' }

      const filename = `meeting_${currentMeetingId.slice(0, 8)}.${ext}`
      await saveFile(content, filename, [{ name: ext.toUpperCase(), extensions: [ext] }])
      showToast(`Đã export ${filename}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [currentMeetingId, saveFile])

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1',
    borderRadius: 8, fontSize: 13, outline: 'none', background: '#f8fafc',
  }
  const btnBase: React.CSSProperties = {
    padding: '9px 18px', borderRadius: 8, border: 'none',
    fontWeight: 600, fontSize: 13, cursor: 'pointer',
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 999,
          padding: '12px 20px', borderRadius: 10, background: '#dcfce7',
          color: '#166534', boxShadow: '0 4px 16px rgba(0,0,0,0.12)', fontSize: 13, fontWeight: 500,
        }}>
          {toast}
        </div>
      )}

      <StepBadge
        step={currentStep}
        audioReady={hasAudio}
        transcriptReady={hasTranscript}
        analysisReady={hasAnalysis}
      />

      {error && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: '#fee2e2', borderRadius: 8, color: '#991b1b', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* STEP 1: Audio */}
      <section style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: '#0f172a' }}>
          🎙️ Bước 1: Audio
        </h3>

        <input
          placeholder="Tiêu đề cuộc họp (tùy chọn)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ ...inputStyle, marginBottom: 12 }}
        />

        {/* Recording controls */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
          {!isRecording ? (
            <button
              onClick={handleStartRecord}
              style={{ ...btnBase, background: '#ef4444', color: '#fff' }}
            >
              ⏺ Ghi âm
            </button>
          ) : (
            <>
              <button
                onClick={handleStopRecord}
                style={{ ...btnBase, background: '#1e293b', color: '#fff' }}
              >
                ⏹ Dừng ({fmtTime(elapsedSeconds)})
              </button>
              <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 600 }}>
                ● ĐANG GHI ({fmtTime(elapsedSeconds)})
              </span>
            </>
          )}
          <button
            onClick={handlePickFile}
            style={{ ...btnBase, background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0' }}
          >
            📂 Tải file audio
          </button>
        </div>

        {audioPath && (
          <div style={{ fontSize: 12, color: '#16a34a', padding: '6px 10px', background: '#f0fdf4', borderRadius: 6 }}>
            ✓ {audioPath.split(/[\\/]/).pop()}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
          <input type="checkbox" id="diarize" checked={diarize} onChange={(e) => setDiarize(e.target.checked)} />
          <label htmlFor="diarize" style={{ fontSize: 12, color: '#64748b' }}>
            Phân biệt người nói (Diarization) — chậm hơn
          </label>
        </div>
      </section>

      {/* STEP 2: Transcript */}
      <section style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontWeight: 700, fontSize: 15, color: '#0f172a' }}>📝 Bước 2: Transcript</h3>
          <button
            onClick={handleTranscribe}
            disabled={!hasAudio || transcribing}
            style={{
              ...btnBase, background: '#0ea5e9', color: '#fff',
              opacity: !hasAudio || transcribing ? 0.5 : 1,
              cursor: !hasAudio || transcribing ? 'not-allowed' : 'pointer',
            }}
          >
            {transcribing ? `⏳ ${transcribeProgress || 'Đang xử lý...'}` : '⚡ Chuyển văn bản'}
          </button>
        </div>
        <textarea
          value={editableTranscript}
          onChange={(e) => setEditableTranscript(e.target.value)}
          placeholder="Transcript sẽ xuất hiện ở đây sau khi transcribe. Bạn có thể chỉnh sửa trước khi phân tích..."
          rows={8}
          style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }}
        />
      </section>

      {/* STEP 3: Analysis */}
      <section style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontWeight: 700, fontSize: 15, color: '#0f172a' }}>🤖 Bước 3: Phân tích</h3>
          <button
            onClick={handleAnalyze}
            disabled={!hasTranscript || analyzing}
            style={{
              ...btnBase, background: '#7c3aed', color: '#fff',
              opacity: !hasTranscript || analyzing ? 0.5 : 1,
              cursor: !hasTranscript || analyzing ? 'not-allowed' : 'pointer',
            }}
          >
            {analyzing ? `⏳ ${analyzeProgress || 'Đang phân tích...'}` : '✨ Phân tích (GPT-4o)'}
          </button>
        </div>

        {hasAnalysis && (
          <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#15803d' }}>
            ✓ Phân tích hoàn thành — {analysis!.epics.length} Epics, {analysis!.epics.reduce((s, e) => s + e.tasks.length, 0)} Tasks
          </div>
        )}
      </section>

      {/* Export + Review */}
      {hasAnalysis && (
        <section style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20 }}>
          <h3 style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', marginBottom: 14 }}>📤 Export &amp; Actions</h3>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button onClick={() => handleExport('markdown')} style={{ ...btnBase, background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0' }}>
              📄 Export Markdown
            </button>
            <button onClick={() => handleExport('json')} style={{ ...btnBase, background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0' }}>
              🗂 Export JSON
            </button>
            <button onClick={() => handleExport('csv')} style={{ ...btnBase, background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0' }}>
              📊 Export CSV
            </button>
            <button
              onClick={onOpenReview}
              style={{ ...btnBase, background: '#2563eb', color: '#fff', marginLeft: 'auto' }}
            >
              📋 Review &amp; Push to Jira →
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

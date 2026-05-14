import { useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { buildUploadFormData, uploadMeetingMedia } from '../api/meetings'
import { createMeeting as createSupabaseMeeting } from '../api/supabase/meetings.api'
import { useFileDialog } from '../hooks/useFileDialog'
import UploadTab from '../components/meeting/UploadTab'

type AudioTab = 'upload' | 'record'

const UI = {
  primary: '#5645d4',
  ink: '#1a1a1a',
  charcoal: '#37352f',
  slate: '#5d5b54',
  steel: '#787671',
  muted: '#bbb8b1',
  canvas: '#ffffff',
  surface: '#f6f5f4',
  surfaceSoft: '#fafaf9',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  error: '#e03131',
  success: '#1aae39',
  warning: '#dd5b00',
  peach: '#ffe8d4',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

export default function NewMeetingView() {
  const {
    audioPath, setAudioPath,
    currentMeetingId, setCurrentMeetingId,
    setCurrentJobId, setProcessingKind,
    setProcessingProgress,
    setCurrentMeetingTitle, resetMeetingState,
    selectedLanguage, selectedDiarize,
    setSelectedLanguage, setSelectedDiarize,
    setRoute,
  } = useAppStore()

  const [title, setTitle] = useState('')
  const [audioTab, setAudioTab] = useState<AudioTab>('upload')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)

  const { openFile } = useFileDialog()

  // Reset meeting-level state when entering this page fresh
  useEffect(() => {
    resetMeetingState()
    setAudioPath(null)
    setTitle('')
    setError(null)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const showToast = useCallback((msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }, [])

  const ensureMeetingId = useCallback(async (): Promise<string> => {
    if (currentMeetingId) return currentMeetingId
    const meetingTitle = title.trim() || `Meeting ${new Date().toLocaleString('vi-VN')}`
    const meeting = await createSupabaseMeeting({ title: meetingTitle })
    setCurrentMeetingId(meeting.id)
    setCurrentMeetingTitle(meeting.title)
    return meeting.id
  }, [currentMeetingId, title, setCurrentMeetingId, setCurrentMeetingTitle])

  // Upload tab: pick file then queue transcription
  const handleStartUpload = useCallback(async () => {
    if (!audioPath) { setError('Chưa chọn file audio hoặc video.'); return }

    setError(null)
    setBusy(true)
    setUploadProgress(0)
    try {
      const meetingId = await ensureMeetingId()

      const electronAPI = (window as unknown as {
        electronAPI?: { readFileBytes: (path: string) => Promise<ArrayBuffer> }
      }).electronAPI
      if (!electronAPI?.readFileBytes) {
        throw new Error('Electron file bridge chưa sẵn sàng. Ứng dụng cần chạy trong Electron.')
      }
      const fileBytes = await electronAPI.readFileBytes(audioPath)
      const formData = buildUploadFormData({
        filePath: audioPath,
        fileBytes,
        diarize: selectedDiarize,
        language: selectedLanguage,
      })

      const resp = await uploadMeetingMedia({
        meetingId,
        formData,
        onUploadProgress: (pct) => {
          setUploadProgress(Math.min(25, Math.round(pct * 0.25)))
        },
      })

      setUploadProgress(25)
      setCurrentJobId(resp.job_id)
      setProcessingKind('transcribing')
      setProcessingProgress(25)
      setRoute('processing')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
      setUploadProgress(null)
    }
  }, [audioPath, selectedDiarize, selectedLanguage, ensureMeetingId, setCurrentJobId, setProcessingKind, setProcessingProgress, setRoute])

  // Record tab: create meeting then navigate to LiveRecordingScreen
  const handleStartRecording = useCallback(async () => {
    setError(null)
    setBusy(true)
    try {
      const meetingTitle = title.trim() || `Meeting ${new Date().toLocaleString('vi-VN')}`
      const meeting = await createSupabaseMeeting({ title: meetingTitle })
      setCurrentMeetingId(meeting.id)
      setCurrentMeetingTitle(meeting.title)
      setRoute('live_recording')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }, [title, setCurrentMeetingId, setCurrentMeetingTitle, setRoute])

  const inputStyle: React.CSSProperties = {
    width: '100%', height: 44, padding: '12px 16px', border: `1px solid ${UI.hairlineStrong}`,
    borderRadius: 8, fontSize: 14, outline: 'none', background: UI.canvas, color: UI.ink,
    boxSizing: 'border-box', fontFamily: UI.font,
  }
  const btnBase: React.CSSProperties = {
    padding: '10px 18px', borderRadius: 8, border: 'none',
    fontWeight: 500, fontSize: 14, cursor: 'pointer', fontFamily: UI.font,
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', fontFamily: UI.font, color: UI.ink }}>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 999,
          padding: '12px 20px', borderRadius: 12, background: '#d9f3e1',
          color: UI.success, boxShadow: 'rgba(15, 15, 15, 0.08) 0px 4px 12px 0px', fontSize: 13, fontWeight: 500,
        }}>
          {toast}
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontWeight: 600, fontSize: 22, lineHeight: 1.3, color: UI.ink, margin: '0 0 4px' }}>Cuộc họp mới</h2>
        <p style={{ color: UI.slate, fontSize: 14, lineHeight: 1.5, margin: 0 }}>Upload file hoặc ghi âm trực tiếp để bắt đầu</p>
      </div>

      {error && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: '#fde0ec', borderRadius: 8, color: UI.error, fontSize: 13 }}>
          {error}
        </div>
      )}

      <div style={{ background: UI.canvas, borderRadius: 12, border: `1px solid ${UI.hairline}`, overflow: 'hidden', marginBottom: 16 }}>
        {/* Title input */}
        <div style={{ padding: '20px 20px 0' }}>
          <input
            placeholder="Tiêu đề cuộc họp (tùy chọn)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={inputStyle}
          />
        </div>

        {/* Tab selector */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${UI.hairline}`, marginTop: 16 }}>
          {(['upload', 'record'] as AudioTab[]).map((tab) => {
            const isActive = audioTab === tab
            return (
              <button
                key={tab}
                onClick={() => { setAudioTab(tab); setError(null) }}
                style={{
                  padding: '12px 24px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: isActive ? `2px solid ${UI.ink}` : '2px solid transparent',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 500,
                  color: isActive ? UI.ink : UI.steel,
                  fontFamily: UI.font,
                }}
              >
                {tab === 'upload' ? '📂 Upload File' : '⏺ Ghi âm'}
              </button>
            )
          })}
        </div>

        {/* Tab content */}
        <div style={{ padding: 20 }}>
          {audioTab === 'upload' ? (
            <>
              <UploadTab
                audioPath={audioPath}
                onAudioPicked={setAudioPath}
                openFile={openFile}
                onToast={showToast}
              />

              {/* Options */}
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: UI.slate, cursor: 'pointer' }}>
                    <input type="checkbox" checked={selectedDiarize} onChange={(e) => setSelectedDiarize(e.target.checked)} />
                    Phân biệt người nói (Diarization)
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: UI.slate }}>
                    Ngôn ngữ:
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      style={{ padding: '4px 8px', borderRadius: 8, border: `1px solid ${UI.hairlineStrong}`, fontSize: 12, background: UI.canvas, color: UI.ink }}
                    >
                      <option value="">Auto-detect</option>
                      <option value="en">English</option>
                      <option value="vi">Tiếng Việt</option>
                    </select>
                  </label>
                </div>
              </div>

              <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
                {busy && uploadProgress !== null && (
                  <div style={{ flex: 1, marginRight: 16, alignSelf: 'center' }}>
                    <div style={{ height: 8, borderRadius: 999, background: UI.hairline, overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${uploadProgress}%`,
                          borderRadius: 999,
                          background: UI.primary,
                          transition: 'width 0.2s ease',
                        }}
                      />
                    </div>
                    <div style={{ marginTop: 6, fontSize: 12, color: UI.steel }}>
                      Upload {uploadProgress}%
                    </div>
                  </div>
                )}
                <button
                  onClick={handleStartUpload}
                  disabled={!audioPath || busy}
                  style={{
                    ...btnBase,
                    background: !audioPath || busy ? UI.hairline : UI.primary,
                    color: '#fff',
                    cursor: !audioPath || busy ? 'not-allowed' : 'pointer',
                    minWidth: 160,
                  }}
                >
                  {busy ? '⏳ Đang upload...' : '⚡ Bắt đầu xử lý'}
                </button>
              </div>
            </>
          ) : (
            /* Record tab */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{
                padding: '28px 20px', border: `1px dashed ${UI.hairlineStrong}`, borderRadius: 12,
                background: UI.peach, textAlign: 'center',
              }}>
                <div style={{ fontSize: 40, marginBottom: 8 }}>🎙️</div>
                <div style={{ fontWeight: 600, color: UI.charcoal, marginBottom: 4 }}>Ghi âm trực tiếp</div>
                <div style={{ fontSize: 12, color: UI.warning }}>
                  Ghi âm từ microphone + audio hệ thống. File WAV 16kHz mono.
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: UI.slate, cursor: 'pointer' }}>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  style={{ padding: '4px 8px', borderRadius: 8, border: `1px solid ${UI.hairlineStrong}`, fontSize: 12, background: UI.canvas, color: UI.ink }}
                >
                  <option value="">Auto-detect</option>
                  <option value="en">English</option>
                  <option value="vi">Tiếng Việt</option>
                </select>
                <span>Ngôn ngữ transcription</span>
              </label>

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={handleStartRecording}
                  disabled={busy}
                  style={{
                    ...btnBase,
                    background: busy ? UI.hairline : UI.ink,
                    color: '#fff',
                    cursor: busy ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 8,
                  }}
                >
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#fff', display: 'inline-block' }} />
                  {busy ? 'Đang khởi tạo...' : 'Bắt đầu ghi âm'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

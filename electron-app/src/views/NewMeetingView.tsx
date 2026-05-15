import { useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { buildUploadFormData, uploadMeetingMedia } from '../api/meetings'
import { createMeeting as createSupabaseMeeting } from '../api/supabase/meetings.api'
import { useFileDialog } from '../hooks/useFileDialog'
import UploadTab from '../components/meeting/UploadTab'
import { Button, Card, Field, Icon, Input, Select, Toast } from '../components/ui'

type AudioTab = 'upload' | 'record'

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

  const handleStartUpload = useCallback(async () => {
    if (!audioPath) { setError('Chưa chọn file audio hoặc video.'); return }
    setError(null)
    setBusy(true)
    setUploadProgress(0)
    try {
      const meetingId = await ensureMeetingId()
      const electronAPI = (window as unknown as { electronAPI?: { readFileBytes: (path: string) => Promise<ArrayBuffer> } }).electronAPI
      if (!electronAPI?.readFileBytes) throw new Error('Electron file bridge chưa sẵn sàng. Ứng dụng cần chạy trong Electron.')
      const fileBytes = await electronAPI.readFileBytes(audioPath)
      const formData = buildUploadFormData({ filePath: audioPath, fileBytes, diarize: selectedDiarize, language: selectedLanguage })
      const resp = await uploadMeetingMedia({ meetingId, formData, onUploadProgress: (pct) => setUploadProgress(Math.min(25, Math.round(pct * 0.25))) })
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

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      {toast && <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 999 }}><Toast type="success" title={toast} /></div>}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontWeight: 800, fontSize: 22, lineHeight: 1.3, color: 'var(--color-text-main)', margin: '0 0 4px' }}>Cuộc họp mới</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.5, margin: 0 }}>Upload file hoặc ghi âm trực tiếp để bắt đầu.</p>
      </div>
      {error && <div style={{ marginBottom: 16, padding: '10px 16px', background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)', borderRadius: 8, color: 'var(--color-danger)', fontSize: 13 }}>{error}</div>}

      <Card style={{ overflow: 'hidden', marginBottom: 16 }}>
        <div style={{ padding: '20px 20px 0' }}>
          <Field label="Tiêu đề cuộc họp">
            <Input placeholder="Tiêu đề cuộc họp (tùy chọn)" value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
        </div>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border-subtle)', marginTop: 16 }}>
          {(['upload', 'record'] as AudioTab[]).map((tab) => {
            const isActive = audioTab === tab
            return (
              <button key={tab} onClick={() => { setAudioTab(tab); setError(null) }} style={{ padding: '12px 24px', background: isActive ? 'var(--color-surface)' : 'var(--color-surface-2)', border: 'none', borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent', cursor: 'pointer', fontSize: 14, fontWeight: 700, color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Icon name={tab === 'upload' ? 'perm_media' : 'radio_button_checked'} size={18} fill={isActive} />
                {tab === 'upload' ? 'Upload File' : 'Ghi âm'}
              </button>
            )
          })}
        </div>
        <div style={{ padding: 20 }}>
          {audioTab === 'upload' ? (
            <>
              <UploadTab audioPath={audioPath} onAudioPicked={setAudioPath} openFile={openFile} onToast={showToast} />
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: 'var(--color-text-muted)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={selectedDiarize} onChange={(e) => setSelectedDiarize(e.target.checked)} />
                    Phân biệt người nói (Diarization)
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: 'var(--color-text-muted)' }}>
                    Ngôn ngữ:
                    <Select value={selectedLanguage} onChange={(e) => setSelectedLanguage(e.target.value)} style={{ width: 150, padding: '6px 28px 6px 10px', fontSize: 12 }}>
                      <option value="">Auto-detect</option>
                      <option value="en">English</option>
                      <option value="vi">Tiếng Việt</option>
                    </Select>
                  </label>
                </div>
              </div>
              <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
                {busy && uploadProgress !== null && (
                  <div style={{ flex: 1, marginRight: 16, alignSelf: 'center' }}>
                    <div style={{ height: 8, borderRadius: 999, background: 'var(--color-surface-3)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${uploadProgress}%`, borderRadius: 999, background: 'var(--color-primary)', transition: 'width 0.2s ease' }} />
                    </div>
                    <div style={{ marginTop: 6, fontSize: 12, color: 'var(--color-text-subtle)' }}>Upload {uploadProgress}%</div>
                  </div>
                )}
                <Button onClick={handleStartUpload} disabled={!audioPath || busy} variant="primary" style={{ minWidth: 172 }}>
                  {busy && <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
                  {busy ? 'Đang upload...' : 'Bắt đầu xử lý'}
                </Button>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <button
                type="button"
                onClick={handleStartRecording}
                disabled={busy}
                style={{
                  width: '100%',
                  padding: '32px 20px',
                  border: '1px dashed var(--color-border)',
                  borderRadius: 14,
                  background: busy ? 'var(--color-surface-2)' : 'var(--color-surface)',
                  textAlign: 'center',
                  cursor: busy ? 'not-allowed' : 'pointer',
                  opacity: busy ? 0.7 : 1,
                  transition: 'border-color 150ms ease-out, background 150ms ease-out, transform 150ms ease-out',
                }}
              >
                <Icon name={busy ? 'progress_activity' : 'mic'} size={44} style={{ color: busy ? 'var(--color-primary)' : 'var(--color-danger)', marginBottom: 10, animation: busy ? 'spin 1s linear infinite' : undefined }} />
                <div style={{ fontWeight: 800, color: 'var(--color-text-main)', marginBottom: 6, fontSize: 16 }}>{busy ? 'Đang khởi tạo ghi âm...' : 'Bấm để bắt đầu ghi âm'}</div>
                <div style={{ fontSize: 13, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>Ghi âm từ microphone + audio hệ thống. File WAV 16kHz mono.</div>
              </button>
              <Field label="Ngôn ngữ transcription:">
                <Select value={selectedLanguage} onChange={(e) => setSelectedLanguage(e.target.value)} style={{ maxWidth: 220 }}>
                  <option value="">Auto-detect</option>
                  <option value="en">English</option>
                  <option value="vi">Tiếng Việt</option>
                </Select>
              </Field>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}


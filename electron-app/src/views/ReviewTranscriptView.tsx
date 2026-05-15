import { useState, useCallback, useEffect, useMemo } from 'react'
import { useAppStore } from '../store/appStore'
import { useTranscriptSegments, useEditTranscriptSegment, useRenameSpeaker } from '../hooks/supabase/useTranscript'
import { startAnalysis } from '../api/meetings'
import type { TranscriptSegment } from '../types/supabase-models'
import { Badge, Button, Card, EmptyState, Field, Icon, Input, Modal } from '../components/ui'

const SPEAKER_COLORS = [
  'var(--color-primary)', 'var(--color-info)', 'var(--color-success)', 'var(--color-warning)', 'var(--color-danger)',
  'var(--color-brand-700)', 'var(--color-brand-400)', 'var(--color-text-muted)', 'var(--color-text-subtle)', 'var(--color-primary-hover)',
]

function speakerColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xffffffff
  return SPEAKER_COLORS[Math.abs(hash) % SPEAKER_COLORS.length]
}

function displaySpeaker(speaker: string | null): string {
  return speaker?.trim() || 'Transcript'
}

function fmtTime(s: number | null): string {
  const safeSeconds = Number.isFinite(s) ? Number(s) : 0
  const m = Math.floor(safeSeconds / 60)
  const sec = Math.floor(safeSeconds % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

interface EditState {
  [segId: string]: string
}

export default function ReviewTranscriptView() {
  const {
    currentMeetingId,
    setCurrentJobId, setProcessingKind, setRoute,
  } = useAppStore()

  const {
    data: segmentsData,
    isLoading: loadingSegs,
    error: fetchError,
  } = useTranscriptSegments(currentMeetingId)

  const segments = segmentsData?.segments ?? []
  const { mutate: editSegment, isPending: isSavingSegment } = useEditTranscriptSegment(currentMeetingId)
  const { mutate: renameSpk } = useRenameSpeaker(currentMeetingId)

  const [editState, setEditState] = useState<EditState>({})
  const [renamingFrom, setRenamingFrom] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [savingSegId, setSavingSegId] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [confirmReAnalyzeOpen, setConfirmReAnalyzeOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!currentMeetingId && !loadingSegs) {
      setRoute('new_meeting')
    }
  }, [currentMeetingId, loadingSegs, setRoute])

  const speakers = useMemo(
    () => Array.from(new Set(segments.map((s) => s.speaker).filter((speaker): speaker is string => !!speaker?.trim()))),
    [segments]
  )

  const handleContentEdit = useCallback((id: string, value: string) => {
    setEditState((prev) => ({ ...prev, [id]: value }))
  }, [])

  const handleContentBlur = useCallback((seg: TranscriptSegment) => {
    const newContent = editState[seg.id]
    if (newContent === undefined || newContent === seg.content) return

    setSavingSegId(seg.id)
    editSegment(
      { segment_id: seg.id, content: newContent },
      {
        onSuccess: () => {
          setEditState((prev) => { const n = { ...prev }; delete n[seg.id]; return n })
        },
        onError: () => setError('Lưu thất bại — nội dung sửa vẫn được giữ, vui lòng thử lại.'),
        onSettled: () => setSavingSegId(null),
      }
    )
  }, [editState, editSegment])

  const handleOpenRename = useCallback((speaker: string) => {
    setRenamingFrom(speaker)
    setRenameValue(speaker)
    setError(null)
  }, [])

  const handleRenameConfirm = useCallback(() => {
    if (!renamingFrom || !renameValue.trim() || !currentMeetingId) return
    const from = renamingFrom
    const to = renameValue.trim()
    setRenamingFrom(null)

    renameSpk(
      { meeting_id: currentMeetingId, from_speaker: from, to_speaker: to },
      {
        onError: () => setError('Rename speaker thất bại — vui lòng thử lại.'),
      }
    )
  }, [renamingFrom, renameValue, currentMeetingId, renameSpk])

  const handleReAnalyze = useCallback(async () => {
    if (!currentMeetingId || segments.length === 0) return

    setConfirmReAnalyzeOpen(false)
    setAnalyzing(true)
    setError(null)
    try {
      const resp = await startAnalysis(currentMeetingId)
      const jobId = resp.job_id
      setCurrentJobId(jobId)
      setProcessingKind('analyzing')
      setRoute('processing')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setAnalyzing(false)
    }
  }, [currentMeetingId, segments.length, setCurrentJobId, setProcessingKind, setRoute])

  if (loadingSegs) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Icon name="progress_activity" size={32} style={{ color: 'var(--color-primary)', animation: 'spin 0.8s linear infinite' }} />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', color: 'var(--color-text-main)' }}>
      <Modal
        open={!!renamingFrom}
        title="Đổi tên người nói"
        onClose={() => setRenamingFrom(null)}
        footer={(
          <>
            <Button variant="outline" onClick={() => setRenamingFrom(null)}>Hủy</Button>
            <Button variant="primary" onClick={handleRenameConfirm} disabled={!renameValue.trim()}>Lưu</Button>
          </>
        )}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
            Tất cả đoạn của <strong style={{ color: renamingFrom ? speakerColor(renamingFrom) : 'var(--color-primary)' }}>{renamingFrom}</strong> sẽ được đổi tên.
          </p>
          <Field label="Tên mới">
            <Input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRenameConfirm() }}
            />
          </Field>
        </div>
      </Modal>


      <Modal
        open={confirmReAnalyzeOpen}
        title="Xác nhận phân tích lại"
        onClose={() => setConfirmReAnalyzeOpen(false)}
        footer={(
          <>
            <Button variant="outline" onClick={() => setConfirmReAnalyzeOpen(false)} disabled={analyzing}>Hủy</Button>
            <Button variant="danger" onClick={handleReAnalyze} disabled={analyzing || segments.length === 0}>
              <Icon name={analyzing ? 'progress_activity' : 'auto_awesome'} size={16} style={analyzing ? { animation: 'spin 0.8s linear infinite' } : undefined} />
              {analyzing ? 'Đang khởi chạy...' : 'Phân tích lại'}
            </Button>
          </>
        )}
      >
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.6 }}>
          <Icon name="warning" size={20} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
          <span>Phân tích lại sẽ thay thế toàn bộ action items cũ của meeting này, bao gồm cả item đã synced lên Jira. Bạn vẫn muốn tiếp tục?</span>
        </div>
      </Modal>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Icon name="article" size={22} style={{ color: 'var(--color-primary)' }} />
            <h2 style={{ fontWeight: 800, fontSize: 22, lineHeight: 1.3, margin: 0 }}>Transcript</h2>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.5, margin: 0 }}>
            Kiểm tra, chỉnh sửa transcript và phân tích lại khi cần.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <Button variant="outline" onClick={() => setRoute('results')}><Icon name="arrow_back" size={16} /> Results</Button>
          <Button variant="secondary" onClick={() => setRoute('review')}><Icon name="rule" size={16} /> Review & Push Jira</Button>
          <Button variant="primary" onClick={() => setConfirmReAnalyzeOpen(true)} disabled={analyzing || segments.length === 0}>
            <Icon name={analyzing ? 'progress_activity' : 'auto_awesome'} size={16} style={analyzing ? { animation: 'spin 0.8s linear infinite' } : undefined} />
            {analyzing ? 'Đang khởi chạy...' : 'Re-analyze'}
          </Button>
        </div>
      </div>

      {(error || fetchError) && (
        <div style={{ marginBottom: 16 }}>
          <Card style={{ padding: 14, background: 'color-mix(in srgb, var(--color-danger) 10%, var(--color-surface))', color: 'var(--color-danger)' }}>
            {error || fetchError?.message}
          </Card>
        </div>
      )}

      <Card style={{ marginBottom: 16, padding: 14, background: 'color-mix(in srgb, var(--color-warning) 10%, var(--color-surface))', color: 'var(--color-warning)' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, lineHeight: 1.5 }}>
          <Icon name="warning" size={18} />
          <span>Re-analyze sẽ tạo lại kết quả phân tích và thay thế toàn bộ action items cũ, bao gồm cả các item đã synced lên Jira.</span>
        </div>
      </Card>

      {speakers.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {speakers.map((sp) => (
            <button
              key={sp}
              onClick={() => handleOpenRename(sp)}
              title="Nhấn để đổi tên"
              style={{
                padding: '5px 10px', borderRadius: 'var(--radius-chip)', border: '1px solid var(--color-border-subtle)',
                background: 'var(--color-surface)', color: speakerColor(sp), fontWeight: 700, fontSize: 12, cursor: 'pointer', display: 'inline-flex', gap: 6, alignItems: 'center',
              }}
            >
              {sp} <Icon name="edit" size={13} />
            </button>
          ))}
        </div>
      )}

      {segments.length === 0 ? (
        <Card><EmptyState icon="speaker_notes_off" title="Không có transcript" description="Thử lại từ đầu hoặc kiểm tra trạng thái xử lý meeting." /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {segments.map((seg) => {
            const speakerName = displaySpeaker(seg.speaker)
            const color = speakerColor(speakerName)
            const editVal = editState[seg.id] ?? seg.content ?? ''
            const isSaving = savingSegId === seg.id && isSavingSegment
            return (
              <Card key={seg.id} style={{ padding: '12px 16px' }}>
                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{ minWidth: 104, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <button
                      onClick={() => { if (seg.speaker) handleOpenRename(seg.speaker) }}
                      title={seg.speaker ? 'Đổi tên người nói' : 'Transcript không có speaker diarization'}
                      style={{
                        padding: '3px 8px', borderRadius: 'var(--radius-chip)', border: '1px solid var(--color-border-subtle)',
                        background: 'var(--color-surface-2)', color, fontWeight: 800, fontSize: 11,
                        cursor: seg.speaker ? 'pointer' : 'default', textAlign: 'left',
                      }}
                    >
                      {speakerName}
                    </button>
                    <Badge size="sm" variant="default">{fmtTime(seg.start_time)} – {fmtTime(seg.end_time)}</Badge>
                  </div>

                  <div style={{ flex: 1, position: 'relative' }}>
                    <textarea
                      value={editVal}
                      onChange={(e) => handleContentEdit(seg.id, e.target.value)}
                      onBlur={() => handleContentBlur(seg)}
                      rows={Math.max(2, Math.ceil(editVal.length / 80))}
                      style={{
                        width: '100%', border: 'none', background: 'transparent', resize: 'none', fontSize: 14,
                        lineHeight: 1.55, color: 'var(--color-text-main)', fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box',
                      }}
                    />
                    {isSaving && (
                      <span style={{ position: 'absolute', top: 0, right: 0, fontSize: 11, color: 'var(--color-text-muted)' }}>
                        lưu...
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <div style={{ marginTop: 32, textAlign: 'right' }}>
        <Button variant="primary" size="lg" onClick={() => setConfirmReAnalyzeOpen(true)} disabled={analyzing || segments.length === 0}>
          <Icon name={analyzing ? 'progress_activity' : 'auto_awesome'} size={18} style={analyzing ? { animation: 'spin 0.8s linear infinite' } : undefined} />
          {analyzing ? 'Đang khởi chạy phân tích lại...' : 'Re-analyze'}
        </Button>
      </div>
    </div>
  )
}




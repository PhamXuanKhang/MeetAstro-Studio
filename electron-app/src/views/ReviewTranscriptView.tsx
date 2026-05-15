import { useState, useCallback, useEffect, useMemo } from 'react'
import { useAppStore } from '../store/appStore'
import { useTranscriptSegments, useEditTranscriptSegment, useRenameSpeaker } from '../hooks/supabase/useTranscript'
import { startAnalysis } from '../api/meetings'
import type { TranscriptSegment } from '../types/supabase-models'

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
  lavender: '#e6e0f5',
  peach: '#ffe8d4',
  warning: '#dd5b00',
  dangerBg: '#fee2e2',
  danger: '#991b1b',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

// Deterministic color per speaker name
const SPEAKER_COLORS = [
  '#5645d4', '#7b3ff2', '#2a9d99', '#dd5b00', '#ff64c8',
  '#1aae39', '#0075de', '#523410', '#a02e6d', '#391c57',
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

  // ─── React Query: fetch segments from Supabase ────────
  const {
    data: segmentsData,
    isLoading: loadingSegs,
    error: fetchError,
  } = useTranscriptSegments(currentMeetingId)

  const segments = segmentsData?.segments ?? []

  // ─── Mutations ────────────────────────────────────────
  const { mutate: editSegment, isPending: isSavingSegment } = useEditTranscriptSegment(currentMeetingId)
  const { mutate: renameSpk } = useRenameSpeaker(currentMeetingId)

  // ─── Local UI State ───────────────────────────────────
  const [editState, setEditState] = useState<EditState>({})
  const [renamingFrom, setRenamingFrom] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [savingSegId, setSavingSegId] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Guard: redirect if missing state
  useEffect(() => {
    if (!currentMeetingId && !loadingSegs) {
      setRoute('new_meeting')
    }
  }, [currentMeetingId, loadingSegs, setRoute])

  // Unique speaker names
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
        onError: () => setError('Lưu thất bại — vui lòng thử lại.'),
        onSettled: () => setSavingSegId(null),
      }
    )
    setEditState((prev) => { const n = { ...prev }; delete n[seg.id]; return n })
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

  // startAnalysis giữ nguyên FastAPI (trigger Celery job)
  const handleReAnalyze = useCallback(async () => {
    if (!currentMeetingId || segments.length === 0) return
    const confirmed = window.confirm(
      'Phân tích lại sẽ thay thế toàn bộ action items cũ của meeting này, bao gồm cả item đã synced lên Jira. Bạn vẫn muốn tiếp tục?'
    )
    if (!confirmed) return

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

  const btnBase: React.CSSProperties = {
    padding: '10px 18px', borderRadius: 8, border: 'none',
    fontWeight: 500, fontSize: 14, cursor: 'pointer', fontFamily: UI.font,
  }

  if (loadingSegs) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <div style={{ width: 32, height: 32, border: `3px solid ${UI.primary}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', fontFamily: UI.font, color: UI.ink }}>
      {/* Speaker rename modal */}
      {renamingFrom && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={(e) => { if (e.target === e.currentTarget) setRenamingFrom(null) }}
        >
          <div style={{ background: UI.canvas, borderRadius: 12, padding: 28, width: 360, boxShadow: 'rgba(15, 15, 15, 0.16) 0px 16px 48px -8px', border: `1px solid ${UI.hairline}` }}>
            <h3 style={{ margin: '0 0 16px', fontWeight: 600, fontSize: 18, color: UI.ink, lineHeight: 1.4 }}>
              Đổi tên người nói
            </h3>
            <p style={{ margin: '0 0 12px', fontSize: 14, color: UI.slate, lineHeight: 1.5 }}>
              Tất cả đoạn của <strong style={{ color: speakerColor(renamingFrom) }}>{renamingFrom}</strong> sẽ được đổi tên:
            </p>
            <input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRenameConfirm() }}
              style={{ width: '100%', height: 44, padding: '12px 16px', border: `1px solid ${UI.hairlineStrong}`, borderRadius: 8, fontSize: 14, boxSizing: 'border-box', marginBottom: 16, color: UI.ink, fontFamily: UI.font }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setRenamingFrom(null)} style={{ ...btnBase, background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}>
                Hủy
              </button>
              <button onClick={handleRenameConfirm} disabled={!renameValue.trim()} style={{ ...btnBase, background: UI.primary, color: '#fff' }}>
                Lưu
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontWeight: 600, fontSize: 22, lineHeight: 1.3, color: UI.ink, margin: '0 0 4px' }}>Transcript</h2>
          <p style={{ color: UI.slate, fontSize: 14, lineHeight: 1.5, margin: 0 }}>
            Kiểm tra, chỉnh sửa transcript và phân tích lại khi cần.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button
            onClick={() => setRoute('results')}
            style={{ ...btnBase, background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}
          >
            ← Results
          </button>
          <button
            onClick={() => setRoute('review')}
            style={{ ...btnBase, background: '#2563eb', color: '#fff' }}
          >
            Review & Push Jira
          </button>
          <button
            onClick={handleReAnalyze}
            disabled={analyzing || segments.length === 0}
            style={{
              ...btnBase,
              background: analyzing || segments.length === 0 ? UI.hairline : UI.primary,
              color: '#fff', fontSize: 14, padding: '11px 22px',
              cursor: analyzing || segments.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            {analyzing ? 'Đang khởi chạy...' : 'Re-analyze'}
          </button>
        </div>
      </div>

      {(error || fetchError) && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: UI.peach, borderRadius: 8, color: UI.warning, fontSize: 13 }}>
          {error || fetchError?.message}
        </div>
      )}

      <div style={{ marginBottom: 16, padding: '10px 16px', background: UI.dangerBg, borderRadius: 8, color: UI.danger, fontSize: 13, lineHeight: 1.5 }}>
        Re-analyze sẽ tạo lại kết quả phân tích và thay thế toàn bộ action items cũ, bao gồm cả các item đã synced lên Jira.
      </div>

      {/* Speaker legend */}
      {speakers.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {speakers.map((sp) => (
            <button
              key={sp}
              onClick={() => handleOpenRename(sp)}
              title="Nhấn để đổi tên"
              style={{
                padding: '4px 12px', borderRadius: 99, border: 'none',
                background: speakerColor(sp) + '22',
                color: speakerColor(sp), fontWeight: 600, fontSize: 12, cursor: 'pointer',
              }}
            >
              {sp} ✎
            </button>
          ))}
        </div>
      )}

      {/* Segments */}
      {segments.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: UI.steel, fontSize: 14 }}>
          Không có transcript — thử lại từ đầu.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {segments.map((seg) => {
            const speakerName = displaySpeaker(seg.speaker)
            const color = speakerColor(speakerName)
            const editVal = editState[seg.id] ?? seg.content ?? ''
            const isSaving = savingSegId === seg.id && isSavingSegment
            return (
              <div
                key={seg.id}
                style={{
                  background: UI.canvas, borderRadius: 12, border: `1px solid ${UI.hairline}`,
                  padding: '12px 16px', display: 'flex', gap: 12,
                }}
              >
                {/* Left: speaker + time */}
                <div style={{ minWidth: 90, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <button
                    onClick={() => { if (seg.speaker) handleOpenRename(seg.speaker) }}
                    title={seg.speaker ? 'Đổi tên người nói' : 'Transcript không có speaker diarization'}
                    style={{
                      padding: '2px 8px', borderRadius: 99, border: 'none',
                      background: color + '22', color, fontWeight: 700, fontSize: 11,
                      cursor: seg.speaker ? 'pointer' : 'default',
                      textAlign: 'left',
                    }}
                  >
                    {speakerName}
                  </button>
                  <span style={{ fontSize: 11, color: UI.steel, fontVariantNumeric: 'tabular-nums' }}>
                    {fmtTime(seg.start_time)} – {fmtTime(seg.end_time)}
                  </span>
                </div>

                {/* Right: editable content */}
                <div style={{ flex: 1, position: 'relative' }}>
                  <textarea
                    value={editVal}
                    onChange={(e) => handleContentEdit(seg.id, e.target.value)}
                    onBlur={() => handleContentBlur(seg)}
                    rows={Math.max(2, Math.ceil(editVal.length / 80))}
                    style={{
                      width: '100%', border: 'none', background: 'transparent',
                      resize: 'none', fontSize: 14, lineHeight: 1.55, color: UI.charcoal,
                      fontFamily: UI.font, outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                  {isSaving && (
                    <span style={{ position: 'absolute', top: 0, right: 0, fontSize: 11, color: UI.steel }}>
                      lưu...
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Sticky bottom Analyze CTA */}
      <div style={{ marginTop: 32, textAlign: 'right' }}>
        <button
          onClick={handleReAnalyze}
          disabled={analyzing || segments.length === 0}
          style={{
            ...btnBase,
            background: analyzing || segments.length === 0 ? UI.hairline : UI.primary,
            color: '#fff', fontSize: 15, padding: '13px 32px',
            cursor: analyzing || segments.length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          {analyzing ? 'Đang khởi chạy phân tích lại...' : 'Re-analyze'}
        </button>
      </div>
    </div>
  )
}


import { useCallback, useEffect, useState } from 'react'
import { deleteMeeting, listMeetings } from '../api/supabase/meetings.api'
import { useAppStore } from '../store/appStore'
import type { MeetingListItem } from '../types/supabase-models'

interface Props {
  onOpenResults: (meeting: MeetingListItem) => void
}

const UI = {
  ink: '#1a1a1a',
  slate: '#5d5b54',
  steel: '#787671',
  muted: '#bbb8b1',
  canvas: '#ffffff',
  surfaceSoft: '#fafaf9',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  lavender: '#e6e0f5',
  primary: '#5645d4',
  error: '#e03131',
  success: '#1aae39',
  warning: '#dd5b00',
}

function fmtDt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function statusColors(status: string): { bg: string; fg: string } {
  if (status === 'pushed') return { bg: '#d9f3e1', fg: UI.success }
  if (status === 'failed') return { bg: '#ffe2e2', fg: UI.error }
  if (status === 'draft' || status === 'approved') return { bg: UI.lavender, fg: UI.primary }
  if (status === 'transcribing' || status === 'analyzing') return { bg: '#dcecfa', fg: '#1168a7' }
  return { bg: UI.surfaceSoft, fg: UI.steel }
}

export default function HistoryView({ onOpenResults }: Props) {
  const [loading, setLoading] = useState(true)
  const [meetings, setMeetings] = useState<MeetingListItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const searchQuery = useAppStore((s) => s.searchQuery)
  const currentMeetingId = useAppStore((s) => s.currentMeetingId)
  const setCurrentMeetingId = useAppStore((s) => s.setCurrentMeetingId)
  const setSelectedMeeting = useAppStore((s) => s.setSelectedMeeting)
  const setMeetingDetail = useAppStore((s) => s.setMeetingDetail)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await listMeetings()
      const missingCounts = resp.items.filter((item) => item.jira_links_count == null)
      if (missingCounts.length > 0) {
        console.warn('[history] missing jira_links_count for meetings:', missingCounts.map((item) => item.id))
      }
      setMeetings(resp.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleDelete = useCallback(async (meeting: MeetingListItem) => {
    const ok = window.confirm(`Xoá cuộc họp "${meeting.title || 'Untitled'}"?`)
    if (!ok) return
    setDeletingId(meeting.id)
    setError(null)
    try {
      await deleteMeeting(meeting.id)
      setMeetings((prev) => prev.filter((item) => item.id !== meeting.id))
      if (currentMeetingId === meeting.id) {
        setCurrentMeetingId(null)
        setSelectedMeeting(null)
        setMeetingDetail(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDeletingId(null)
    }
  }, [currentMeetingId, setCurrentMeetingId, setMeetingDetail, setSelectedMeeting])

  const q = searchQuery.trim().toLowerCase()
  const filtered = q ? meetings.filter((m) => m.title.toLowerCase().includes(q)) : meetings

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24, color: UI.steel }}>
        <div style={{ width: 20, height: 20, border: `2px solid ${UI.primary}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        Đang tải lịch sử...
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {error && (
        <div style={{ marginBottom: 16, padding: 12, background: '#fee2e2', borderRadius: 10, color: '#991b1b', fontSize: 13 }}>
          {error}
        </div>
      )}
      <div style={{ background: UI.canvas, borderRadius: 16, border: `1px solid ${UI.hairline}`, overflow: 'hidden' }}>
        {filtered.length === 0 ? (
          <p style={{ padding: 24, color: UI.muted, fontSize: 13 }}>
            {q ? 'Không tìm thấy kết quả.' : 'Chưa có lịch sử cuộc họp.'}
          </p>
        ) : (
          filtered.map((m, i) => {
            const colors = statusColors(m.status)
            return (
              <div
                key={m.id}
                onClick={() => onOpenResults(m)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '14px 20px',
                  cursor: 'pointer',
                  borderBottom: i < filtered.length - 1 ? `1px solid ${UI.hairline}` : 'none',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = UI.surfaceSoft)}
                onMouseLeave={(e) => (e.currentTarget.style.background = '')}
              >
                <span style={{ width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', background: UI.surfaceSoft, color: UI.steel, border: `1px solid ${UI.hairline}` }}>
                  M
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 650, fontSize: 14, color: UI.ink, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {m.title || 'Untitled'}
                  </div>
                  <div style={{ fontSize: 11, color: UI.steel, marginTop: 4 }}>
                    {fmtDt(m.created_at)}
                  </div>
                </div>
                <span style={{ padding: '4px 10px', borderRadius: 999, background: colors.bg, color: colors.fg, fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>
                  {m.status}
                </span>
                <span style={{ minWidth: 86, textAlign: 'right', fontSize: 12, color: UI.slate }}>
                  {m.jira_links_count ?? 0} Jira links
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(m)
                  }}
                  disabled={deletingId === m.id}
                  style={{
                    border: `1px solid ${UI.hairlineStrong}`,
                    background: UI.canvas,
                    color: UI.error,
                    borderRadius: 8,
                    padding: '6px 10px',
                    cursor: deletingId === m.id ? 'default' : 'pointer',
                    opacity: deletingId === m.id ? 0.6 : 1,
                    fontSize: 12,
                  }}
                >
                  {deletingId === m.id ? 'Đang xoá...' : 'Xoá'}
                </button>
                <span style={{ color: UI.muted, fontSize: 18 }}>›</span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

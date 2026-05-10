import { useMemo, useState, useCallback } from 'react'
import { useMeetingsList, useDeleteMeeting } from '../hooks/supabase/useMeetings'
import { useAppStore } from '../store/appStore'
import type { MeetingsListResult } from '../types/supabase-models'

type MeetingItem = MeetingsListResult['items'][number]

interface Props {
  onOpenResults: (meeting: MeetingItem) => void
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
  const searchQuery = useAppStore((s) => s.searchQuery)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // React Query: auto fetch + cache
  const { data, isLoading, error } = useMeetingsList({ limit: 100 })
  const { mutate: remove } = useDeleteMeeting()

  const items = data?.items ?? []

  // Client-side search filter
  const q = searchQuery.trim().toLowerCase()
  const filtered = useMemo(
    () => q ? items.filter((m) => (m.title ?? '').toLowerCase().includes(q)) : items,
    [items, q]
  )

  const handleDelete = useCallback((e: React.MouseEvent, meetingId: string) => {
    e.stopPropagation() // Ngăn click mở meeting
    if (!confirm('Bạn có chắc muốn xoá cuộc họp này?')) return
    setDeletingId(meetingId)
    remove(meetingId, {
      onSettled: () => setDeletingId(null),
    })
  }, [remove])

  if (isLoading) {
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
        <div style={{ marginBottom: 16, padding: 12, background: '#fee2e2', borderRadius: 8, color: '#991b1b', fontSize: 13 }}>
          {error.message}
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
              <button
                onClick={(e) => handleDelete(e, m.id)}
                disabled={deletingId === m.id}
                title="Xoá cuộc họp"
                style={{
                  padding: '4px 8px', borderRadius: 6, border: '1px solid #e2e8f0',
                  background: deletingId === m.id ? '#fee2e2' : 'transparent',
                  color: '#991b1b', cursor: 'pointer', fontSize: 12,
                  opacity: deletingId === m.id ? 0.5 : 0.6,
                  transition: 'opacity 0.15s',
                }}
                onMouseEnter={(e) => { if (deletingId !== m.id) e.currentTarget.style.opacity = '1' }}
                onMouseLeave={(e) => { if (deletingId !== m.id) e.currentTarget.style.opacity = '0.6' }}
              >
                {deletingId === m.id ? '⏳' : '🗑'}
              </button>
              <span style={{ color: '#cbd5e1', fontSize: 18 }}>›</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

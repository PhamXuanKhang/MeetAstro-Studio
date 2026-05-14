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

export default function HistoryView({ onOpenResults }: Props) {
  const searchQuery = useAppStore((s) => s.searchQuery)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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
    setDeleteError(null)
    setDeletingId(meetingId)
    remove(meetingId, {
      onError: (err) => setDeleteError(err.message),
      onSettled: () => setDeletingId(null),
    })
  }, [remove])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24, color: '#64748b' }}>
        <div style={{ width: 20, height: 20, border: '2px solid #0ea5e9', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
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
      {deleteError && (
        <div style={{ marginBottom: 16, padding: 12, background: '#fee2e2', borderRadius: 8, color: '#991b1b', fontSize: 13 }}>
          {deleteError}
        </div>
      )}
      <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        {filtered.length === 0 ? (
          <p style={{ padding: 24, color: '#94a3b8', fontSize: 13 }}>
            {q ? 'Không tìm thấy kết quả.' : 'Chưa có lịch sử cuộc họp.'}
          </p>
        ) : (
          filtered.map((m, i) => (
            <div
              key={m.id}
              onClick={() => onOpenResults(m)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '14px 20px',
                cursor: 'pointer',
                borderBottom: i < filtered.length - 1 ? '1px solid #f1f5f9' : 'none',
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
              onMouseLeave={(e) => (e.currentTarget.style.background = '')}
            >
              <span style={{ fontSize: 18 }}>📄</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>
                  {m.title || 'Untitled'}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                  {fmtDt(m.created_at)}
                </div>
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

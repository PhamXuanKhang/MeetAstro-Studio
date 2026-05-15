import { useMemo, useState, useCallback } from 'react'
import { useMeetingsList, useDeleteMeeting } from '../hooks/supabase/useMeetings'
import { useAppStore } from '../store/appStore'
import type { MeetingsListResult } from '../types/supabase-models'
import { Button, Card, EmptyState, Icon } from '../components/ui'

type MeetingItem = MeetingsListResult['items'][number]

interface Props { onOpenResults: (meeting: MeetingItem) => void }

function fmtDt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

export default function HistoryView({ onOpenResults }: Props) {
  const searchQuery = useAppStore((s) => s.searchQuery)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const { data, isLoading, error } = useMeetingsList({ limit: 100 })
  const { mutate: remove } = useDeleteMeeting()
  const items = data?.items ?? []
  const q = searchQuery.trim().toLowerCase()
  const filtered = useMemo(() => q ? items.filter((m) => (m.title ?? '').toLowerCase().includes(q)) : items, [items, q])

  const handleDelete = useCallback((e: React.MouseEvent, meetingId: string) => {
    e.stopPropagation()
    if (!confirm('Bạn có chắc muốn xoá cuộc họp này?')) return
    setDeleteError(null)
    setDeletingId(meetingId)
    remove(meetingId, { onError: (err) => setDeleteError(err.message), onSettled: () => setDeletingId(null) })
  }, [remove])

  if (isLoading) return (
    <Card style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24, color: 'var(--color-text-muted)' }}>
      <Icon name="progress_activity" size={20} style={{ color: 'var(--color-primary)', animation: 'spin 1s linear infinite' }} />
      Đang tải lịch sử...
    </Card>
  )

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {error && <div style={{ marginBottom: 16, padding: 12, background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)', borderRadius: 8, color: 'var(--color-danger)', fontSize: 13 }}>{error.message}</div>}
      {deleteError && <div style={{ marginBottom: 16, padding: 12, background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)', borderRadius: 8, color: 'var(--color-danger)', fontSize: 13 }}>{deleteError}</div>}
      <Card style={{ overflow: 'hidden' }}>
        {filtered.length === 0 ? (
          <EmptyState icon="history" title={q ? 'Không tìm thấy kết quả' : 'Chưa có lịch sử cuộc họp'} description={q ? 'Thử thay đổi từ khóa tìm kiếm.' : 'Các cuộc họp đã xử lý sẽ xuất hiện tại đây.'} />
        ) : filtered.map((m, i) => (
          <div key={m.id} onClick={() => onOpenResults(m)} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px', cursor: 'pointer', borderBottom: i < filtered.length - 1 ? '1px solid var(--color-border-subtle)' : 'none', transition: 'background 0.1s' }}>
            <Icon name="description" size={20} style={{ color: 'var(--color-text-muted)' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.title || 'Untitled'}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>{fmtDt(m.created_at)}</div>
            </div>
            <Button onClick={(e) => handleDelete(e, m.id)} disabled={deletingId === m.id} title="Xoá cuộc họp" variant="ghost" size="sm" style={{ color: 'var(--color-danger)', opacity: deletingId === m.id ? 0.5 : 0.8 }}>
              <Icon name={deletingId === m.id ? 'progress_activity' : 'delete'} size={16} style={deletingId === m.id ? { animation: 'spin 1s linear infinite' } : undefined} />
            </Button>
            <Icon name="chevron_right" size={18} style={{ color: 'var(--color-text-subtle)' }} />
          </div>
        ))}
      </Card>
    </div>
  )
}

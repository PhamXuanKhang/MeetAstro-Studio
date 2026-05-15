import { useMemo } from 'react'
import { useMeetingsList } from '../hooks/supabase/useMeetings'
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

function MeetingCard({ meeting, onOpen }: { meeting: MeetingItem; onOpen: () => void }) {
  return (
    <Card hover onClick={onOpen} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: 16, cursor: 'pointer' }}>
      <div style={{ width: 44, height: 44, borderRadius: 8, background: 'var(--color-bg)', border: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-primary)', flexShrink: 0 }}>
        <Icon name="mic" size={22} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--color-text-main)', marginBottom: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{meeting.title || 'Untitled'}</div>
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{fmtDt(meeting.created_at)}</div>
      </div>
      <Icon name="chevron_right" size={18} style={{ color: 'var(--color-text-subtle)' }} />
    </Card>
  )
}

export default function DashboardView({ onOpenResults }: Props) {
  const searchQuery = useAppStore((s) => s.searchQuery)
  const { data, isLoading, error, refetch } = useMeetingsList({ limit: 50 })
  const items = data?.items ?? []
  const q = searchQuery.trim().toLowerCase()
  const meetings = useMemo(() => q ? items.filter((m) => (m.title ?? '').toLowerCase().includes(q)) : items, [items, q])

  if (isLoading) return (
    <Card style={{ maxWidth: 1100, margin: '0 auto', padding: 48, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
      <Icon name="progress_activity" size={32} style={{ color: 'var(--color-primary)', animation: 'spin 1s linear infinite' }} />
      <p style={{ color: 'var(--color-text-muted)', fontSize: 13, margin: 0 }}>Đang tải...</p>
    </Card>
  )

  if (error) return (
    <Card style={{ maxWidth: 1100, margin: '0 auto', padding: 24, background: 'color-mix(in srgb, var(--color-danger) 10%, var(--color-surface))', color: 'var(--color-danger)' }}>
      Không thể tải danh sách: {error.message}
      <Button onClick={() => refetch()} variant="outline" size="sm" style={{ marginLeft: 12, color: 'var(--color-danger)' }}>Thử lại</Button>
    </Card>
  )

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--color-text-main)', margin: 0 }}>{meetings.length} cuộc họp</h2>
          {q && <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--color-text-muted)' }}>Tìm kiếm: “{searchQuery}”</p>}
        </div>
        <Button onClick={() => refetch()} variant="secondary" size="sm"><Icon name="sync" size={16} />Làm mới</Button>
      </div>
      {meetings.length === 0 ? (
        <Card><EmptyState icon="mic" title="Chưa có cuộc họp nào" description="Bắt đầu bằng cách ghi âm hoặc tải file audio." /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{meetings.map((m) => <MeetingCard key={m.id} meeting={m} onOpen={() => onOpenResults(m)} />)}</div>
      )}
    </div>
  )
}

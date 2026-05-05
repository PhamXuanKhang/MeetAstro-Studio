import { useEffect, useState, useCallback } from 'react'
import { listMeetings } from '../api/meetings'
import { useAppStore } from '../store/appStore'
import type { MeetingResponse } from '../types/schema'

interface Props {
  onOpenResults: (meeting: MeetingResponse) => void
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

function MeetingCard({ meeting, onOpen }: { meeting: MeetingResponse; onOpen: () => void }) {
  const subtitle = fmtDt(meeting.created_at)

  return (
    <div
      onClick={onOpen}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: 16,
        background: '#fff',
        borderRadius: 16,
        border: '1px solid #e2e8f0',
        cursor: 'pointer',
        transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.10)')}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = '')}
    >
      <div
        style={{
          width: 44, height: 44,
          borderRadius: 14,
          background: '#f0fdfa',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, flexShrink: 0,
        }}
      >
        🎙️
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', marginBottom: 3 }}>
          {meeting.title || 'Untitled'}
        </div>
        <div style={{ fontSize: 11, color: '#64748b' }}>{subtitle}</div>
      </div>
      <span style={{ color: '#94a3b8', fontSize: 18 }}>›</span>
    </div>
  )
}

export default function DashboardView({ onOpenResults }: Props) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { searchQuery, cachedMeetings, setCachedMeetings } = useAppStore()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await listMeetings()
      setCachedMeetings(resp.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [setCachedMeetings])

  useEffect(() => {
    load()
  }, [load])

  const q = searchQuery.trim().toLowerCase()
  const meetings = q
    ? cachedMeetings.filter((m) => m.title.toLowerCase().includes(q))
    : cachedMeetings

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 48, gap: 12 }}>
        <div style={{ width: 32, height: 32, border: '3px solid #0ea5e9', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <p style={{ color: '#64748b', fontSize: 13 }}>Đang tải...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24, background: '#fee2e2', borderRadius: 12, color: '#991b1b' }}>
        Không thể tải danh sách: {error}
        <button onClick={load} style={{ marginLeft: 12, padding: '4px 10px', borderRadius: 6, border: '1px solid #991b1b', background: 'transparent', color: '#991b1b', cursor: 'pointer' }}>
          Thử lại
        </button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
          {meetings.length} cuộc họp{q ? ` (tìm kiếm: "${searchQuery}")` : ''}
        </h2>
        <button
          onClick={load}
          style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontSize: 12, color: '#64748b' }}
        >
          🔄 Làm mới
        </button>
      </div>

      {meetings.length === 0 ? (
        <div style={{ padding: 24, background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0' }}>
          <p style={{ fontWeight: 700, marginBottom: 6 }}>Chưa có cuộc họp nào.</p>
          <p style={{ fontSize: 12, color: '#64748b' }}>Bắt đầu bằng cách ghi âm hoặc tải file audio.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {meetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} onOpen={() => onOpenResults(m)} />
          ))}
        </div>
      )}
    </div>
  )
}

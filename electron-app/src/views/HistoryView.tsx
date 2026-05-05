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

export default function HistoryView({ onOpenResults }: Props) {
  const [loading, setLoading] = useState(true)
  const [meetings, setMeetings] = useState<MeetingResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const searchQuery = useAppStore((s) => s.searchQuery)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await listMeetings()
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

  const q = searchQuery.trim().toLowerCase()
  const filtered = q ? meetings.filter((m) => m.title.toLowerCase().includes(q)) : meetings

  if (loading) {
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
          {error}
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
              <span style={{ color: '#cbd5e1', fontSize: 18 }}>›</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

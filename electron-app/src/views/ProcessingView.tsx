import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../store/appStore'
import { pollJobStatus } from '../api/meetings'
import { subscribeMeetingStatus, unsubscribeChannel } from '../api/supabase/realtime'
import type { JobStatusResponse, MeetingStatus } from '../types/supabase-models'

const UI = {
  primary: '#5645d4',
  ink: '#1a1a1a',
  slate: '#5d5b54',
  steel: '#787671',
  canvas: '#ffffff',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  error: '#e03131',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Đang chuẩn bị xử lý...',
  transcribing: 'Đang chuyển âm thanh thành transcript...',
  transcribed: 'Transcript đã sẵn sàng, đang chuẩn bị phân tích...',
  analyzing: 'Đang phân tích và tạo action items...',
  draft: 'Hoàn tất. Đang mở kết quả phân tích...',
  failed: 'Xử lý thất bại',
}

function fmtElapsed(s: number) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`
}

function getProgressFloor(status: string): number {
  if (status === 'analyzing') return 60
  if (status === 'draft') return 100
  return 25
}

function getProgressCeiling(status: string): number {
  if (status === 'transcribing' || status === 'transcribed') return 60
  if (status === 'analyzing') return 90
  if (status === 'draft') return 100
  return 25
}

export default function ProcessingView() {
  const {
    currentJobId,
    currentMeetingId,
    processingKind,
    processingProgress,
    setProcessingProgress,
    setProcessingMessage,
    setMeetingStatus,
    setRoute,
  } = useAppStore()

  const [status, setStatus] = useState<MeetingStatus | 'pending'>('pending')
  const [localProgress, setLocalProgress] = useState(processingProgress ?? 25)
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const routedRef = useRef(false)

  const jobQuery = useQuery<JobStatusResponse, Error>({
    queryKey: ['job-status', currentJobId],
    queryFn: () => pollJobStatus(currentJobId!),
    enabled: Boolean(currentJobId) && !routedRef.current,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      return state === 'SUCCESS' || state === 'FAILURE' ? false : 2000
    },
  })

  useEffect(() => {
    if (!currentJobId || !currentMeetingId || !processingKind) {
      setRoute('new_meeting')
    }
  }, [currentJobId, currentMeetingId, processingKind, setRoute])

  useEffect(() => {
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!currentMeetingId) return

    const channel = subscribeMeetingStatus(currentMeetingId, (update) => {
      setStatus(update.status)
      setMeetingStatus(update.status)
      if (update.error_message) {
        setError(update.error_message)
      }
      if (update.status === 'failed') {
        setError(update.error_message || 'Pipeline xử lý thất bại.')
      }
    })

    return () => { unsubscribeChannel(channel) }
  }, [currentMeetingId, setMeetingStatus])

  useEffect(() => {
    const job = jobQuery.data
    if (!job) return

    if (job.state === 'FAILURE') {
      setError(job.error || 'Pipeline xử lý thất bại.')
      return
    }

    if (job.state === 'SUCCESS') {
      setStatus('draft')
    }
  }, [jobQuery.data])

  useEffect(() => {
    if (jobQuery.error) {
      setError(jobQuery.error.message)
    }
  }, [jobQuery.error])

  useEffect(() => {
    if (error) return

    const floor = getProgressFloor(status)
    const ceiling = getProgressCeiling(status)
    setLocalProgress((prev) => Math.max(prev, floor))

    if (status === 'draft') {
      setLocalProgress(100)
      setProcessingProgress(100)
      setProcessingMessage(STATUS_LABELS.draft)
      if (!routedRef.current) {
        routedRef.current = true
        window.setTimeout(() => setRoute('results'), 700)
      }
      return
    }

    const timer = window.setInterval(() => {
      setLocalProgress((prev) => {
        const next = prev < ceiling ? Math.min(ceiling, prev + 1) : prev
        setProcessingProgress(next)
        return next
      })
    }, status === 'pending' ? 2500 : 1200)

    return () => window.clearInterval(timer)
  }, [error, status, setProcessingMessage, setProcessingProgress, setRoute])

  useEffect(() => {
    const message = STATUS_LABELS[status] ?? 'Đang xử lý...'
    setProcessingMessage(message)
  }, [status, setProcessingMessage])

  const handleRetry = () => setRoute('new_meeting')
  const handleGoHistory = () => setRoute('history')

  return (
    <div style={{ maxWidth: 560, margin: '80px auto 0', padding: '0 24px', textAlign: 'center', fontFamily: UI.font, color: UI.ink }}>
      {!error ? (
        <>
          <div style={{ fontSize: 52, marginBottom: 20 }}>⏳</div>
          <h2 style={{ fontWeight: 600, fontSize: 22, lineHeight: 1.3, color: UI.ink, marginBottom: 8 }}>
            {STATUS_LABELS[status] ?? 'Đang xử lý...'}
          </h2>

          <div style={{ background: UI.hairline, borderRadius: 9999, height: 8, overflow: 'hidden', margin: '24px 0 12px' }}>
            <div
              style={{
                height: '100%',
                borderRadius: 99,
                background: UI.primary,
                width: `${Math.max(25, Math.min(100, localProgress))}%`,
                transition: 'width 0.45s ease',
              }}
            />
          </div>

          <p style={{ fontSize: 14, color: UI.slate, margin: '0 0 4px', lineHeight: 1.5 }}>
            {Math.round(localProgress)}%
          </p>
          <p style={{ fontSize: 12, color: UI.steel }}>
            Đã chờ {fmtElapsed(elapsed)}
          </p>
        </>
      ) : (
        <>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✕</div>
          <h2 style={{ fontWeight: 600, fontSize: 18, color: UI.ink, marginBottom: 8 }}>Xử lý thất bại</h2>
          <p style={{ fontSize: 13, color: UI.slate, marginBottom: 24, wordBreak: 'break-word' }}>{error}</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={handleRetry}
              style={{
                padding: '10px 18px', borderRadius: 8, border: `1px solid ${UI.hairlineStrong}`,
                background: UI.canvas, color: UI.ink, fontWeight: 500, fontSize: 14, cursor: 'pointer', fontFamily: UI.font,
              }}
            >
              Tạo cuộc họp mới
            </button>
            <button
              onClick={handleGoHistory}
              style={{
                padding: '10px 18px', borderRadius: 8, border: 'none',
                background: UI.primary, color: '#fff', fontWeight: 500, fontSize: 14, cursor: 'pointer', fontFamily: UI.font,
              }}
            >
              Xem lịch sử
            </button>
          </div>
        </>
      )}
    </div>
  )
}

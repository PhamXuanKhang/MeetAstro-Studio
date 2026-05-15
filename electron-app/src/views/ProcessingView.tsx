import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../store/appStore'
import { pollJobStatus } from '../api/meetings'
import { subscribeMeetingStatus, unsubscribeChannel } from '../api/supabase/realtime'
import type { JobStatusResponse, MeetingStatus } from '../types/supabase-models'
import { Button, Card, Icon } from '../components/ui'

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
    processingDoneRoute,
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
    if (!currentJobId || !currentMeetingId || !processingKind) setRoute('new_meeting')
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
      if (update.error_message) setError(update.error_message)
      if (update.status === 'failed') setError(update.error_message || 'Pipeline xử lý thất bại.')
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
    if (job.state === 'SUCCESS') setStatus('draft')
  }, [jobQuery.data])

  useEffect(() => {
    if (jobQuery.error) setError(jobQuery.error.message)
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
        window.setTimeout(() => setRoute(processingDoneRoute ?? 'results'), 700)
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
  }, [error, processingDoneRoute, status, setProcessingMessage, setProcessingProgress, setRoute])

  useEffect(() => {
    setProcessingMessage(STATUS_LABELS[status] ?? 'Đang xử lý...')
  }, [status, setProcessingMessage])

  const handleRetry = () => setRoute('new_meeting')
  const handleGoHistory = () => setRoute('history')

  return (
    <Card style={{ maxWidth: 560, margin: '56px auto 0', padding: '40px 32px', textAlign: 'center' }}>
      {!error ? (
        <>
          <Icon name="progress_activity" size={52} style={{ marginBottom: 20, color: 'var(--color-primary)', animation: 'spin 1s linear infinite' }} />
          <h2 style={{ fontWeight: 700, fontSize: 22, lineHeight: 1.3, color: 'var(--color-text-main)', margin: '0 0 8px' }}>
            {STATUS_LABELS[status] ?? 'Đang xử lý...'}
          </h2>
          <div style={{ background: 'var(--color-surface-3)', borderRadius: 9999, height: 8, overflow: 'hidden', margin: '24px 0 12px' }}>
            <div style={{ height: '100%', borderRadius: 99, background: 'var(--color-primary)', width: `${Math.max(25, Math.min(100, localProgress))}%`, transition: 'width 0.45s ease' }} />
          </div>
          <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: '0 0 4px', lineHeight: 1.5 }}>{Math.round(localProgress)}%</p>
          <p style={{ fontSize: 12, color: 'var(--color-text-subtle)' }}>Đã chờ {fmtElapsed(elapsed)}</p>
        </>
      ) : (
        <>
          <Icon name="error" size={48} style={{ marginBottom: 16, color: 'var(--color-danger)' }} />
          <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--color-text-main)', marginBottom: 8 }}>Xử lý thất bại</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 24, wordBreak: 'break-word' }}>{error}</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button onClick={handleRetry} variant="secondary">Tạo cuộc họp mới</Button>
            <Button onClick={handleGoHistory} variant="primary">Xem lịch sử</Button>
          </div>
        </>
      )}
    </Card>
  )
}

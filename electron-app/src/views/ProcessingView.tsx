import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import { getAnalysis, getMeeting, getTranscriptSegments } from '../api/meetings'
import { pollJob } from '../api/jobs'
import type { JobStatusResponse } from '../types/schema'

const UI = {
  primary: '#5645d4',
  ink: '#1a1a1a',
  slate: '#5d5b54',
  steel: '#787671',
  muted: '#bbb8b1',
  canvas: '#ffffff',
  surface: '#f6f5f4',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  error: '#e03131',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

const PROCESSING_META: Record<string, { label: string; icon: string; successRoute: string }> = {
  transcribing: { label: 'Đang chuyển đổi âm thanh', icon: '🎙️', successRoute: 'review_transcript' },
  finalizing_recording: { label: 'Đang xử lý bản ghi', icon: '🎙️', successRoute: 'review_transcript' },
  analyzing: { label: 'Đang phân tích với GPT-4o', icon: '🤖', successRoute: 'results' },
}

const INDETERMINATE_MSGS: Record<string, string[]> = {
  transcribing: ['Đang upload...', 'Đang transcribe...', 'Xử lý âm thanh...', 'Sắp xong...'],
  finalizing_recording: ['Đang upload bản ghi...', 'Đang transcribe...', 'Sắp xong...'],
  analyzing: ['Đang phân tích...', 'Đang trích xuất action items...', 'Đang xây dựng cây Epic/Task...', 'Sắp xong...'],
}

export default function ProcessingView() {
  const {
    currentJobId, currentMeetingId, processingKind,
    setProcessingProgress, setProcessingMessage,
    setTranscriptSegments, setAnalysis, setSelectedMeeting,
    setRoute,
  } = useAppStore()

  const [localProgress, setLocalProgress] = useState<number | null>(null)
  const [localMessage, setLocalMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const abortRef = useRef<AbortController | null>(null)
  const indetermIdx = useRef(0)
  const startTs = useRef(Date.now())

  const meta = processingKind ? PROCESSING_META[processingKind] : null
  const indetermsForKind = processingKind ? INDETERMINATE_MSGS[processingKind] : []

  // Guard: redirect if missing state
  useEffect(() => {
    if (!currentJobId || !currentMeetingId || !processingKind) {
      setRoute('new_meeting')
    }
  }, [currentJobId, currentMeetingId, processingKind, setRoute])

  // Elapsed timer (for indeterminate UX)
  useEffect(() => {
    startTs.current = Date.now()
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startTs.current) / 1000)), 1000)
    return () => clearInterval(t)
  }, [])

  // Indeterminate message cycling when no progress_pct
  useEffect(() => {
    if (localProgress !== null) return
    const t = setInterval(() => {
      indetermIdx.current = (indetermIdx.current + 1) % indetermsForKind.length
      setLocalMessage(indetermsForKind[indetermIdx.current] ?? '')
    }, 3500)
    setLocalMessage(indetermsForKind[0] ?? '')
    return () => clearInterval(t)
  }, [localProgress, processingKind]) // eslint-disable-line react-hooks/exhaustive-deps

  // Main polling effect
  useEffect(() => {
    if (!currentJobId || !currentMeetingId || !processingKind) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const onProgress = (job: JobStatusResponse) => {
      if (job.progress_pct != null) {
        setLocalProgress(job.progress_pct)
        setProcessingProgress(job.progress_pct)
      }
      if (job.message) {
        setLocalMessage(job.message)
        setProcessingMessage(job.message)
      }
    }

    const run = async () => {
      try {
        await pollJob(currentJobId, 600000, 2000, controller.signal, onProgress)

        // Post-success data fetch
        if (processingKind === 'transcribing' || processingKind === 'finalizing_recording') {
          const segments = await getTranscriptSegments(currentMeetingId)
          setTranscriptSegments(segments)
          setRoute('review_transcript')
        } else {
          const [analysis, meeting] = await Promise.all([
            getAnalysis(currentMeetingId),
            getMeeting(currentMeetingId),
          ])
          setAnalysis(analysis.analysis_json)
          setSelectedMeeting(meeting)
          setRoute('results')
        }
      } catch (e) {
        if (controller.signal.aborted) return
        setError(e instanceof Error ? e.message : String(e))
      }
    }

    run()
    return () => controller.abort()
  }, [currentJobId, currentMeetingId, processingKind]) // eslint-disable-line react-hooks/exhaustive-deps

  const fmtElapsed = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`
  }

  const handleRetry = () => setRoute('new_meeting')
  const handleGoHistory = () => setRoute('history')

  return (
    <div style={{ maxWidth: 520, margin: '80px auto 0', padding: '0 24px', textAlign: 'center', fontFamily: UI.font, color: UI.ink }}>
      {!error ? (
        <>
          <div style={{ fontSize: 56, marginBottom: 20 }}>{meta?.icon ?? '⏳'}</div>
          <h2 style={{ fontWeight: 600, fontSize: 22, lineHeight: 1.3, color: UI.ink, marginBottom: 8 }}>
            {meta?.label ?? 'Đang xử lý...'}
          </h2>

          {/* Progress bar */}
          <div style={{ background: UI.hairline, borderRadius: 9999, height: 8, overflow: 'hidden', margin: '24px 0 12px' }}>
            {localProgress !== null ? (
              <div
                style={{
                  height: '100%', borderRadius: 99, background: UI.primary,
                  width: `${localProgress}%`, transition: 'width 0.4s ease',
                }}
              />
            ) : (
              <div
                style={{
                  height: '100%', borderRadius: 99, background: UI.primary,
                  width: '40%',
                  animation: 'slide 1.6s ease-in-out infinite',
                }}
              />
            )}
          </div>
          <style>{`@keyframes slide {
            0%   { margin-left: -40%; width: 40%; }
            50%  { margin-left: 30%; width: 40%; }
            100% { margin-left: 100%; width: 40%; }
          }`}</style>

          <p style={{ fontSize: 14, color: UI.slate, margin: '0 0 4px', lineHeight: 1.5 }}>
            {localProgress !== null ? `${Math.round(localProgress)}%` : localMessage}
          </p>
          <p style={{ fontSize: 12, color: UI.steel }}>Đã chờ {fmtElapsed(elapsed)}</p>
        </>
      ) : (
        <>
          <div style={{ fontSize: 48, marginBottom: 16 }}>❌</div>
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
              ← Tạo cuộc họp mới
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

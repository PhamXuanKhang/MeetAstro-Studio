import { useEffect, useCallback, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import { useRecording } from '../hooks/useRecording'

const UI = {
  primary: '#5645d4',
  ink: '#1a1a1a',
  charcoal: '#37352f',
  slate: '#5d5b54',
  steel: '#787671',
  muted: '#bbb8b1',
  canvas: '#ffffff',
  surface: '#f6f5f4',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  navy: '#0a1530',
  error: '#e03131',
  peach: '#ffe8d4',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function cleanTranscriptText(text: string): string {
  return text.replace(/<\|\d+(?:\.\d+)?\|>/g, '').replace(/\s+/g, ' ').trim()
}

interface LiveSegment {
  speaker: string
  start: number
  end: number
  text: string
}

export default function LiveRecordingView() {
  const {
    currentMeetingId,
    setRecordingPath, miniPopupOpen, setMiniPopupOpen, setRoute,
  } = useAppStore()

  const { isRecording, elapsedSeconds, error: recError, startRecording, stopRecording } = useRecording()
  const [error, setError] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const [liveSegments, setLiveSegments] = useState<LiveSegment[]>([])
  const [streamDone, setStreamDone] = useState(false)
  const [streamStarted, setStreamStarted] = useState(false)
  const startRequestedRef = useRef(false)
  const transcriptRef = useRef<HTMLDivElement | null>(null)

  // Guard
  useEffect(() => {
    if (!currentMeetingId) { setRoute('new_meeting'); return }
  }, [currentMeetingId, setRoute])

  // Auto-start recording when screen mounts
  useEffect(() => {
    if (!currentMeetingId || startRequestedRef.current) return
    startRequestedRef.current = true
    ;(async () => {
      const apiBaseUrl = await window.electronAPI?.getApiUrl?.()
      const result = await startRecording({
        meeting_id: currentMeetingId,
        api_base_url: apiBaseUrl,
        stream_enabled: Boolean(currentMeetingId && apiBaseUrl),
      })
      setStreamStarted(Boolean(result?.streaming))
      if (result?.streamError) {
        setError('Không thể mở live transcript. File WAV local vẫn được ghi để fallback.')
      }
    })().catch((e) => {
      const message = e instanceof Error ? e.message : String(e)
      setError(`Không thể bắt đầu ghi âm: ${message}`)
    })
    return () => {
      // Unmount without explicit Stop: leave recording running (user may navigate back)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (recError) setError(recError)
  }, [recError])

  useEffect(() => {
    if (!currentMeetingId || !streamStarted) return
    let events: EventSource | null = null
    let cancelled = false

    ;(async () => {
      const apiBaseUrl = await window.electronAPI?.getApiUrl?.()
      if (!apiBaseUrl || cancelled) return
      events = new EventSource(`${apiBaseUrl.replace(/\/$/, '')}/api/v1/meetings/${currentMeetingId}/recording/events`)
      events.onopen = () => {
        console.info('[LiveRecording] SSE opened')
      }
      events.addEventListener('partial', (event) => {
        try {
          console.info('[LiveRecording] SSE partial raw:', (event as MessageEvent).data)
          const payload = JSON.parse((event as MessageEvent).data) as { segments?: LiveSegment[] }
          const segments = (payload.segments ?? [])
            .map((segment) => ({ ...segment, text: cleanTranscriptText(segment.text) }))
            .filter((segment) => segment.text)
          console.info('[LiveRecording] SSE partial segments:', segments.length)
          setLiveSegments(segments)
        } catch (e) {
          console.error('[LiveRecording] SSE partial parse failed:', e)
          setError('Live transcript payload không hợp lệ.')
        }
      })
      events.addEventListener('done', () => {
        console.info('[LiveRecording] SSE done')
        setStreamDone(true)
        events?.close()
      })
      events.addEventListener('error', (event) => {
        console.error('[LiveRecording] SSE error:', event)
        setError('Kết nối live transcript bị gián đoạn. File WAV local vẫn được giữ để fallback.')
        events?.close()
      })
    })().catch((e) => setError(e instanceof Error ? e.message : String(e)))

    return () => {
      cancelled = true
      events?.close()
    }
  }, [currentMeetingId, streamStarted])

  const latestTranscriptLine = liveSegments.at(-1)?.text

  useEffect(() => {
    if (!transcriptRef.current) return
    transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
  }, [liveSegments])

  const handleStop = useCallback(async () => {
    if (stopping) return
    setStopping(true)
    setError(null)
    try {
      const outputPath = await stopRecording()
      if (!outputPath) throw new Error('Không nhận được đường dẫn file ghi âm.')

      setRecordingPath(outputPath)
      setStreamDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStopping(false)
    }
  }, [stopping, stopRecording, setRecordingPath])

  // Sync elapsed time to PIP window while recording — defined after handleStop
  useEffect(() => {
    if (!miniPopupOpen || !isRecording) return
    window.electronAPI?.updatePipState?.({ isRecording, elapsedSeconds, lastTranscriptLine: latestTranscriptLine })
  }, [elapsedSeconds, isRecording, latestTranscriptLine, miniPopupOpen])

  // Listen for stop signal forwarded from PIP window
  useEffect(() => {
    const cleanup = window.electronAPI?.onPipStopRequest?.(() => { handleStop() })
    return () => cleanup?.()
  }, [handleStop])

  // Sync miniPopupOpen when OS closes PIP window unexpectedly
  useEffect(() => {
    const cleanup = window.electronAPI?.onPipClosed?.(() => { setMiniPopupOpen(false) })
    return () => cleanup?.()
  }, [setMiniPopupOpen])

  const handleOpenPip = useCallback(async () => {
    const api = window.electronAPI
    if (api?.openPip) {
      await api.openPip({ isRecording, elapsedSeconds, lastTranscriptLine: latestTranscriptLine })
      setMiniPopupOpen(true)
    } else {
      setMiniPopupOpen(true)
    }
  }, [isRecording, elapsedSeconds, latestTranscriptLine, setMiniPopupOpen])

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center', paddingTop: 40, fontFamily: UI.font, color: UI.ink }}>
      {/* Recording indicator */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ position: 'relative', display: 'inline-block', marginBottom: 16 }}>
          <div style={{
            width: 80, height: 80, borderRadius: '50%', background: isRecording ? UI.peach : UI.surface,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: isRecording ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: isRecording ? UI.error : UI.muted }} />
          </div>
        </div>
        <style>{`@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.4)} 50%{box-shadow:0 0 0 16px rgba(239,68,68,0)} }`}</style>

        <h2 style={{ fontWeight: 600, fontSize: 22, color: UI.ink, lineHeight: 1.3, margin: '0 0 8px' }}>
          {isRecording ? 'Đang ghi âm' : stopping ? 'Đang xử lý...' : 'Chuẩn bị ghi âm...'}
        </h2>

        <div style={{ fontSize: 36, fontWeight: 600, color: UI.error, fontVariantNumeric: 'tabular-nums', letterSpacing: 2, marginBottom: 8 }}>
          {fmtTime(elapsedSeconds)}
        </div>

        {isRecording && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 3, marginBottom: 16, height: 20 }}>
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                style={{
                  width: 4, borderRadius: 2, background: UI.error,
                  height: `${20 + Math.sin(Date.now() / 200 + i) * 10}%`,
                  animation: `wave${i % 3} ${0.8 + (i % 4) * 0.15}s ease-in-out infinite alternate`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Transcript placeholder */}
      <div style={{
        background: UI.surface, borderRadius: 12, border: `1px solid ${UI.hairline}`,
        padding: '20px', marginBottom: 32, textAlign: 'left', minHeight: 100,
      }}>
        <div style={{ fontSize: 11, color: UI.steel, marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
          Live Transcript
        </div>
        {liveSegments.length > 0 ? (
          <div ref={transcriptRef} style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 220, overflowY: 'auto' }}>
            {liveSegments.map((segment, idx) => (
              <div key={`${segment.start}-${segment.end}-${idx}`} style={{ fontSize: 14, lineHeight: 1.5, color: UI.charcoal }}>
                <span style={{ color: UI.primary, fontWeight: 600 }}>{segment.speaker}: </span>
                <span>{segment.text}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: UI.steel, fontSize: 14, lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>
            Đang chờ transcript trực tiếp từ WhisperLiveKit.
          </p>
        )}
        {streamDone && (
          <div style={{ marginTop: 10, fontSize: 12, color: UI.steel }}>Live stream đã hoàn tất.</div>
        )}
      </div>

      {error && (
        <div style={{ marginBottom: 20, padding: '10px 16px', background: '#fde0ec', borderRadius: 8, color: UI.error, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={handleOpenPip}
          disabled={!isRecording}
          style={{
            padding: '10px 18px', borderRadius: 8, border: `1px solid ${UI.hairlineStrong}`,
            background: UI.canvas, color: UI.ink, fontWeight: 500, fontSize: 14, cursor: isRecording ? 'pointer' : 'not-allowed', fontFamily: UI.font,
            opacity: isRecording ? 1 : 0.4,
          }}
        >
          ⊞ Mini Popup
        </button>

        <button
          onClick={handleStop}
          disabled={stopping || !isRecording}
          style={{
            padding: '10px 18px', borderRadius: 8, border: 'none',
            background: stopping || !isRecording ? UI.hairline : UI.ink,
            color: '#fff', fontWeight: 500, fontSize: 14, cursor: stopping || !isRecording ? 'not-allowed' : 'pointer', fontFamily: UI.font,
          }}
        >
          {stopping ? '⏳ Đang xử lý...' : '⏹ Dừng ghi âm'}
        </button>
      </div>

      {/* PIP mini-window: renders in separate always-on-top BrowserWindow (see MiniPopupView.tsx) */}
    </div>
  )
}

import { useEffect, useCallback, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import { useRecording } from '../hooks/useRecording'
import { Button, Card, Icon } from '../components/ui'

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function cleanTranscriptText(text: string): string {
  return text.replace(/<\|\d+(?:\.\d+)?\|>/g, '').replace(/\s+/g, ' ').trim()
}

interface LiveSegment { speaker: string; start: number; end: number; text: string }

export default function LiveRecordingView() {
  const { currentMeetingId, setRecordingPath, miniPopupOpen, setMiniPopupOpen, setRoute } = useAppStore()
  const { isRecording, elapsedSeconds, error: recError, startRecording, stopRecording } = useRecording()
  const [error, setError] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const [liveSegments, setLiveSegments] = useState<LiveSegment[]>([])
  const [streamDone, setStreamDone] = useState(false)
  const [streamStarted, setStreamStarted] = useState(false)
  const startRequestedRef = useRef(false)
  const transcriptRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { if (!currentMeetingId) { setRoute('new_meeting'); return } }, [currentMeetingId, setRoute])

  useEffect(() => {
    if (!currentMeetingId || startRequestedRef.current) return
    startRequestedRef.current = true
    ;(async () => {
      const apiBaseUrl = await window.electronAPI?.getApiUrl?.()
      const result = await startRecording({ meeting_id: currentMeetingId, api_base_url: apiBaseUrl, stream_enabled: Boolean(currentMeetingId && apiBaseUrl) })
      setStreamStarted(Boolean(result?.streaming))
      if (result?.streamError) setError('Không thể mở live transcript. File WAV local vẫn được ghi để fallback.')
    })().catch((e) => setError(`Không thể bắt đầu ghi âm: ${e instanceof Error ? e.message : String(e)}`))
    return () => {}
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (recError) setError(recError) }, [recError])

  useEffect(() => {
    if (!currentMeetingId || !streamStarted) return
    let events: EventSource | null = null
    let cancelled = false
    ;(async () => {
      const apiBaseUrl = await window.electronAPI?.getApiUrl?.()
      if (!apiBaseUrl || cancelled) return
      events = new EventSource(`${apiBaseUrl.replace(/\/$/, '')}/api/v1/meetings/${currentMeetingId}/recording/events`)
      events.onopen = () => { console.info('[LiveRecording] SSE opened') }
      events.addEventListener('partial', (event) => {
        try {
          console.info('[LiveRecording] SSE partial raw:', (event as MessageEvent).data)
          const payload = JSON.parse((event as MessageEvent).data) as { segments?: LiveSegment[] }
          const segments = (payload.segments ?? []).map((segment) => ({ ...segment, text: cleanTranscriptText(segment.text) })).filter((segment) => segment.text)
          console.info('[LiveRecording] SSE partial segments:', segments.length)
          setLiveSegments(segments)
        } catch (e) {
          console.error('[LiveRecording] SSE partial parse failed:', e)
          setError('Live transcript payload không hợp lệ.')
        }
      })
      events.addEventListener('done', () => { console.info('[LiveRecording] SSE done'); setStreamDone(true); events?.close() })
      events.addEventListener('error', (event) => { console.error('[LiveRecording] SSE error:', event); setError('Kết nối live transcript bị gián đoạn. File WAV local vẫn được giữ để fallback.'); events?.close() })
    })().catch((e) => setError(e instanceof Error ? e.message : String(e)))
    return () => { cancelled = true; events?.close() }
  }, [currentMeetingId, streamStarted])

  const latestTranscriptLine = liveSegments.at(-1)?.text

  useEffect(() => { if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight }, [liveSegments])

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

  useEffect(() => { if (miniPopupOpen && isRecording) window.electronAPI?.updatePipState?.({ isRecording, elapsedSeconds, lastTranscriptLine: latestTranscriptLine }) }, [elapsedSeconds, isRecording, latestTranscriptLine, miniPopupOpen])
  useEffect(() => { const cleanup = window.electronAPI?.onPipStopRequest?.(() => { handleStop() }); return () => cleanup?.() }, [handleStop])
  useEffect(() => { const cleanup = window.electronAPI?.onPipClosed?.(() => { setMiniPopupOpen(false) }); return () => cleanup?.() }, [setMiniPopupOpen])

  const handleOpenPip = useCallback(async () => {
    const api = window.electronAPI
    if (api?.openPip) { await api.openPip({ isRecording, elapsedSeconds, lastTranscriptLine: latestTranscriptLine }); setMiniPopupOpen(true) }
    else setMiniPopupOpen(true)
  }, [isRecording, elapsedSeconds, latestTranscriptLine, setMiniPopupOpen])

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center', paddingTop: 32 }}>
      <Card style={{ padding: 32, marginBottom: 24 }}>
        <div style={{ position: 'relative', display: 'inline-flex', marginBottom: 16 }}>
          <div style={{ width: 84, height: 84, borderRadius: '50%', background: isRecording ? 'color-mix(in srgb, var(--color-danger) 10%, var(--color-surface))' : 'var(--color-surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: isRecording ? 'pulse 1.5s ease-in-out infinite' : 'none' }}>
            <Icon name="mic" size={34} style={{ color: isRecording ? 'var(--color-danger)' : 'var(--color-text-subtle)' }} />
          </div>
        </div>
        <style>{`@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 color-mix(in srgb, var(--color-danger) 30%, transparent)} 50%{box-shadow:0 0 0 16px transparent} }`}</style>
        <h2 style={{ fontWeight: 800, fontSize: 22, color: 'var(--color-text-main)', lineHeight: 1.3, margin: '0 0 8px' }}>{isRecording ? 'Đang ghi âm' : stopping ? 'Đang xử lý...' : 'Chuẩn bị ghi âm...'}</h2>
        <div style={{ fontSize: 38, fontWeight: 800, color: 'var(--color-danger)', fontVariantNumeric: 'tabular-nums', letterSpacing: 2, marginBottom: 8 }}>{fmtTime(elapsedSeconds)}</div>
        {isRecording && <div style={{ display: 'flex', justifyContent: 'center', gap: 3, marginBottom: 8, height: 20 }}>{Array.from({ length: 12 }).map((_, i) => <div key={i} style={{ width: 4, borderRadius: 2, background: 'var(--color-danger)', height: `${20 + Math.sin(Date.now() / 200 + i) * 10}%`, animation: `wave${i % 3} ${0.8 + (i % 4) * 0.15}s ease-in-out infinite alternate` }} />)}</div>}
      </Card>

      <Card style={{ padding: 20, marginBottom: 24, textAlign: 'left', minHeight: 120 }}>
        <div style={{ fontSize: 11, color: 'var(--color-text-subtle)', marginBottom: 8, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1 }}>Live Transcript</div>
        {liveSegments.length > 0 ? (
          <div ref={transcriptRef} className="custom-scrollbar" style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 220, overflowY: 'auto' }}>
            {liveSegments.map((segment, idx) => <div key={`${segment.start}-${segment.end}-${idx}`} style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--color-text-main)' }}><span style={{ color: 'var(--color-primary)', fontWeight: 700 }}>{segment.speaker}: </span><span>{segment.text}</span></div>)}
          </div>
        ) : <p style={{ color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>Đang chờ transcript trực tiếp từ WhisperLiveKit.</p>}
        {streamDone && <div style={{ marginTop: 10, fontSize: 12, color: 'var(--color-text-muted)' }}>Live stream đã hoàn tất.</div>}
      </Card>

      {error && <div style={{ marginBottom: 20, padding: '10px 16px', background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)', borderRadius: 8, color: 'var(--color-danger)', fontSize: 13 }}>{error}</div>}

      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <Button onClick={handleOpenPip} disabled={!isRecording} variant="secondary"><Icon name="picture_in_picture_alt" size={18} />Mini Popup</Button>
        <Button onClick={handleStop} disabled={stopping || !isRecording} variant="danger">
          <Icon name={stopping ? 'progress_activity' : 'stop_circle'} size={18} style={stopping ? { animation: 'spin 1s linear infinite' } : undefined} />
          {stopping ? 'Đang xử lý...' : 'Dừng ghi âm'}
        </Button>
      </div>
    </div>
  )
}

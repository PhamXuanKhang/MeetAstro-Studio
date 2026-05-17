import { useEffect, useCallback, useRef, useState } from 'react'
import { useAppStore } from '../store/appStore'
import { useRecording } from '../hooks/useRecording'
import { Button, Card, Icon } from '../components/ui'
import type { AudioLevelEvent, LiveSegment } from '../types/electron'

function cleanTranscriptText(text: string): string {
  return text.replace(/<\|\d+(?:\.\d+)?\|>/g, '').replace(/\s+/g, ' ').trim()
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function levelPercent(rms: number): number {
  return Math.max(0, Math.min(100, Math.round((rms / 6000) * 100)))
}

function AudioLevelBar({ label, rms, peak }: { label: string; rms: number; peak: number }) {
  const percent = levelPercent(rms)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr 96px', gap: 8, alignItems: 'center', fontSize: 12 }}>
      <span style={{ color: 'var(--color-text-muted)', fontWeight: 700 }}>{label}</span>
      <div style={{ height: 8, borderRadius: 999, background: 'var(--color-surface-2)', overflow: 'hidden' }}>
        <div style={{ width: `${percent}%`, height: '100%', borderRadius: 999, background: percent > 0 ? 'var(--color-primary)' : 'var(--color-border)' }} />
      </div>
      <span style={{ color: 'var(--color-text-subtle)', fontVariantNumeric: 'tabular-nums' }}>rms {rms} / pk {peak}</span>
    </div>
  )
}

export default function LiveRecordingView() {
  const {
    currentMeetingId,
    selectedLanguage,
    setCurrentJobId,
    setProcessingKind,
    setProcessingMessage,
    setRecordingPath,
    miniPopupOpen,
    setMiniPopupOpen,
    setRoute,
  } = useAppStore()
  const { isRecording, elapsedSeconds, error: recError, startRecording, stopRecording } = useRecording()
  const [error, setError] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const [liveSegments, setLiveSegments] = useState<LiveSegment[]>([])
  const [streamDone, setStreamDone] = useState(false)
  const [audioLevel, setAudioLevel] = useState<AudioLevelEvent | null>(null)
  const [silentChunks, setSilentChunks] = useState(0)
  const startRequestedRef = useRef(false)
  const latestTranscriptLine = liveSegments.at(-1)?.text
  const isSilent = Boolean(audioLevel && audioLevel.chunk_index >= 10 && silentChunks >= 3)

  useEffect(() => { if (!currentMeetingId) { setRoute('new_meeting'); return } }, [currentMeetingId, setRoute])

  useEffect(() => {
    if (!currentMeetingId || startRequestedRef.current) return
    startRequestedRef.current = true
    ;(async () => {
      const apiBaseUrl = await window.electronAPI?.getApiUrl?.()
      const language = selectedLanguage || 'auto'
      const result = await startRecording({ meeting_id: currentMeetingId, api_base_url: apiBaseUrl, stream_enabled: Boolean(currentMeetingId && apiBaseUrl), language })
      if (result?.streamError) setError(`Không thể mở live transcript qua WebSocket: ${result.streamError}`)
    })().catch((e) => setError(`Không thể bắt đầu ghi âm: ${e instanceof Error ? e.message : String(e)}`))
  }, [currentMeetingId, selectedLanguage, startRecording])

  useEffect(() => { if (recError) setError(recError) }, [recError])
  useEffect(() => {
    const cleanup = window.electronAPI?.onStreamPartial?.((segments) => {
      setLiveSegments(segments.map((segment) => ({ ...segment, text: cleanTranscriptText(segment.text) })).filter((segment) => segment.text))
    })
    return () => cleanup?.()
  }, [])
  useEffect(() => {
    const cleanup = window.electronAPI?.onAudioLevel?.((level) => {
      setAudioLevel(level)
      const silent = level.sys_peak === 0 && level.mic_peak === 0 && level.mixed_peak === 0
      setSilentChunks((count) => (silent ? count + 1 : 0))
    })
    return () => cleanup?.()
  }, [])

  const handleStop = useCallback(async () => {
    if (stopping) return
    setStopping(true)
    setError(null)
    try {
      const result = await stopRecording()
      if (!result?.outputPath) throw new Error('Không nhận được đường dẫn file ghi âm.')
      setRecordingPath(result.outputPath)
      setStreamDone(true)
      const jobId = result.streamResult?.job_id
      const persistedSegments = result.streamResult?.persisted_segments ?? 0
      if (result.streamError) throw new Error(`WebSocket live transcript lỗi khi dừng: ${result.streamError}`)
      if (persistedSegments === 0 || result.streamResult?.no_transcript) {
        const detail = isSilent
          ? 'Audio đang bị silent nên không tạo được transcript. Hãy kiểm tra microphone/system audio rồi ghi lại.'
          : 'Backend nhận stream nhưng WhisperLiveKit chưa trả transcript hợp lệ. Hãy kiểm tra dịch vụ transcription.'
        throw new Error(detail)
      }
      if (!jobId && persistedSegments > 0) {
        setRoute('review_transcript')
        return
      }
      if (!jobId) throw new Error('Không nhận được job xử lý transcript live.')
      setCurrentJobId(jobId)
      setProcessingKind('finalizing_recording')
      setProcessingMessage('Đang hoàn tất transcript live...')
      setRoute('processing')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStopping(false)
    }
  }, [
    stopping,
    stopRecording,
    setRecordingPath,
    setCurrentJobId,
    setProcessingKind,
    setProcessingMessage,
    setRoute,
    isSilent,
  ])

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
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8, textAlign: 'left' }}>
          <AudioLevelBar label="System" rms={audioLevel?.sys_rms ?? 0} peak={audioLevel?.sys_peak ?? 0} />
          <AudioLevelBar label="Mic" rms={audioLevel?.mic_rms ?? 0} peak={audioLevel?.mic_peak ?? 0} />
          <AudioLevelBar label="Mixed" rms={audioLevel?.mixed_rms ?? 0} peak={audioLevel?.mixed_peak ?? 0} />
        </div>
        {isSilent && <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 8, background: 'color-mix(in srgb, var(--color-warning) 12%, transparent)', border: '1px solid color-mix(in srgb, var(--color-warning) 35%, transparent)', color: 'var(--color-warning)', fontSize: 12, lineHeight: 1.4 }}>Không phát hiện tín hiệu audio trong nhiều chunk liên tiếp. App vẫn tiếp tục ghi và gửi WebSocket; hãy kiểm tra microphone/system audio.</div>}
      </Card>

      <Card style={{ padding: 20, marginBottom: 24, textAlign: 'left', minHeight: 120 }}>
        <div style={{ fontSize: 11, color: 'var(--color-text-subtle)', marginBottom: 8, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1 }}>Live Transcript</div>
        {liveSegments.length > 0 ? (
          <div className="custom-scrollbar" style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 220, overflowY: 'auto' }}>
            {liveSegments.map((segment, idx) => <div key={`${segment.start}-${segment.end}-${idx}`} style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--color-text-main)' }}><span style={{ color: 'var(--color-primary)', fontWeight: 700 }}>{segment.speaker}: </span><span>{segment.text}</span></div>)}
          </div>
        ) : <p style={{ color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>Đang stream audio tới FastAPI qua WebSocket. Transcript sẽ mở ở bước review sau khi dừng ghi âm.</p>}
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